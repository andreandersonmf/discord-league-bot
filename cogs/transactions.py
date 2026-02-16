from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime

from db.session import get_session
from db.models import TransactionRequest, Team, Player
from utils.checks import can_open_transactions, can_review_transactions
from utils.roblox import username_to_user_id, roblox_headshot_url
from config import CFG


# ----------------------------
# ROLE OPTIONS
# ----------------------------
ROLE_KEYS = ("Vice Captain", "Court Captain", "Player")

def role_key_to_id(role_key: str) -> int:
    if role_key == "Vice Captain":
        return CFG.ROLE_VICE_CAPTAIN_ID
    if role_key == "Court Captain":
        return CFG.ROLE_COURT_CAPTAIN_ID
    return CFG.ROLE_PLAYER_ID


# ----------------------------
# EMBED COLORS (sidebar)
# ----------------------------
PENDING_COLOR  = 0x0F1115
ACCEPTED_COLOR = 0x00FF3A
DENIED_COLOR   = 0xFF1A1A


async def get_roblox_assets(member: discord.Member) -> tuple[int | None, str | None]:
    rbx_name = member.display_name  # Bloxlink nickname = Roblox username
    rbx_id = await username_to_user_id(rbx_name)
    if not rbx_id:
        return None, None
    headshot = await roblox_headshot_url(rbx_id, "150x150")
    return rbx_id, headshot


def profile_link_button(roblox_user_id: int | None) -> discord.ui.Button:
    if not roblox_user_id:
        return discord.ui.Button(label="Profile", style=discord.ButtonStyle.secondary, disabled=True)

    url = f"https://www.roblox.com/users/{roblox_user_id}/profile"
    return discord.ui.Button(
        label="Profile",
        emoji="↗️",
        style=discord.ButtonStyle.link,
        url=url
    )


def _team_name(session, team_id: int | None) -> str:
    if not team_id:
        return "Free Agent"
    t = session.query(Team).filter_by(id=team_id).first()
    return t.name if t else "Unknown"


async def _ensure_player_row(session, guild_id: int, member: discord.Member) -> Player:
    """Garante que existe row de Player e atualiza username."""
    row = session.query(Player).filter_by(guild_id=guild_id, user_id=member.id).first()
    if not row:
        row = Player(guild_id=guild_id, user_id=member.id, username=str(member))
        session.add(row)
        session.flush()
    else:
        row.username = str(member)
    return row


def _infer_team_from_roles(session, member: discord.Member) -> Team | None:
    """Fallback: tenta achar time pelo cargo do time (teams.role_id)."""
    teams = session.query(Team).all()
    member_role_ids = {r.id for r in member.roles}
    for t in teams:
        if t.role_id in member_role_ids:
            return t
    return None


async def _get_requester_team(session, guild_id: int, requester: discord.Member) -> Team | None:
    """
    Regra: time do requester vem do DB (players.team_id).
    Se não existir (DB novo), tenta inferir pelo cargo do time e cria/atualiza player_row.
    """
    requester_row = session.query(Player).filter_by(guild_id=guild_id, user_id=requester.id).first()
    if requester_row and requester_row.team_id:
        return session.query(Team).filter_by(id=requester_row.team_id).first()

    # fallback por roles
    inferred = _infer_team_from_roles(session, requester)
    if inferred:
        requester_row = await _ensure_player_row(session, guild_id, requester)
        requester_row.team_id = inferred.id
        session.commit()
        return inferred

    return None


def _common_embed_layout(
    *,
    color: int,
    title: str,
    requested_by: discord.Member,
    body: str,
    actor_label: str,
    actor_member: discord.Member | None,
    reason: str | None,
    thumb_url: str | None,
) -> discord.Embed:
    emb = discord.Embed(color=color)
    emb.title = title
    emb.description = body

    # Requested by: pequeno, sem ping
    emb.add_field(name="Requested by", value=f"{requested_by.name}", inline=False)

    # Approved/Denied: COM ping + username
    if actor_member:
        emb.add_field(
            name=actor_label,
            value=f"{actor_member.mention} ({actor_member.name})",
            inline=False
        )
    else:
        emb.add_field(name=actor_label, value="—", inline=False)

    # Reason SEMPRE (pra manter tamanho parecido)
    emb.add_field(name="Reason", value=(reason or "—"), inline=False)

    if thumb_url:
        emb.set_thumbnail(url=thumb_url)

    emb.set_footer(text="CVR Services")
    return emb


async def build_pending_embed(
    session,
    *,
    tx: TransactionRequest,
    requester: discord.Member,
    target: discord.Member,
    to_team_name: str,
) -> tuple[discord.Embed, int | None]:
    rbx_id, headshot = await get_roblox_assets(target)

    if tx.action == "ADD":
        body = f"{target.mention} → **{to_team_name}** as **{tx.requested_role}**"
        title = "Pending Transaction"
    elif tx.action == "REMOVE":
        body = f"{target.mention} → **Free Agent**"
        title = "Pending Transaction"
    else:
        # Transfer 2-step
        stage = "Waiting for player acceptance (0/2)" if not tx.player_confirmed else "Accepted by player — waiting for Transaction Team (1/2)"
        body = f"{target.mention} → **{to_team_name}**\n\n*{stage}*"
        title = "Pending Transfer"

    emb = _common_embed_layout(
        color=PENDING_COLOR,
        title=title,
        requested_by=requester,
        body=body,
        actor_label="Status",
        actor_member=None,
        reason=None,
        thumb_url=headshot,
    )
    return emb, rbx_id


async def build_result_embed(
    session,
    *,
    success: bool,
    tx: TransactionRequest,
    requester: discord.Member,
    actor: discord.Member,
    target: discord.Member,
    to_team_name: str,
) -> tuple[discord.Embed, int | None]:
    rbx_id, headshot = await get_roblox_assets(target)

    title = "Successful Transfer" if success else "Unsuccessful Transfer"
    color = ACCEPTED_COLOR if success else DENIED_COLOR

    # descrição com espaço/respiração
    if tx.action == "ADD":
        body = f"{target.mention} → **{to_team_name}** as **{tx.requested_role}**"
    elif tx.action == "REMOVE":
        body = f"{target.mention} → **Free Agent**"
    else:
        body = f"{target.mention} → **{to_team_name}**"

    emb = _common_embed_layout(
        color=color,
        title=title,
        requested_by=requester,
        body=body,
        actor_label="Approved by" if success else "Denied by",
        actor_member=actor,
        reason=(tx.reason if not success else None),
        thumb_url=headshot,
    )
    return emb, rbx_id


# ----------------------------
# Deny modal (Transaction Team)
# ----------------------------
class DenyReasonModal(discord.ui.Modal, title="Deny Transaction"):
    reason = discord.ui.TextInput(
        label="Reason",
        placeholder="Ex: full roster / already in a team / wrong request ...",
        style=discord.TextStyle.short,
        required=True,
        max_length=120
    )

    def __init__(self, tx_id: int):
        super().__init__()
        self.tx_id = tx_id

    async def on_submit(self, interaction: discord.Interaction):
        member = interaction.user
        if not isinstance(member, discord.Member):
            await interaction.response.send_message("Use isso no servidor.", ephemeral=True)
            return

        if not can_review_transactions(member):
            await interaction.response.send_message("Sem permissão.", ephemeral=True)
            return

        session = get_session()
        try:
            tx = session.get(TransactionRequest, self.tx_id)
            if not tx or tx.status != "PENDING":
                await interaction.response.send_message("Transaction inválida.", ephemeral=True)
                return

            tx.status = "REJECTED"
            tx.reason = str(self.reason.value)
            tx.reviewed_by = interaction.user.id
            tx.reviewed_at = datetime.utcnow()
            session.commit()

            guild = interaction.guild
            target = guild.get_member(tx.target_user_id) if guild else None
            requester = guild.get_member(tx.requested_by) if guild else None

            to_team_name = _team_name(session, tx.to_team_id)
            emb, rbx_id = await build_result_embed(
                session,
                success=False,
                tx=tx,
                requester=requester or member,
                actor=member,
                target=target or member,
                to_team_name=to_team_name,
            )

            await interaction.response.edit_message(embed=emb, view=TxReviewView.profile_only(rbx_id))

        finally:
            session.close()


# ----------------------------
# VIEW
# ----------------------------
class TxReviewView(discord.ui.View):
    def __init__(self, tx_id: int, roblox_user_id: int | None):
        super().__init__(timeout=None)
        self.tx_id = tx_id
        self.roblox_user_id = roblox_user_id

        # order: Profile first
        self.add_item(profile_link_button(roblox_user_id))

    @staticmethod
    def profile_only(roblox_user_id: int | None) -> discord.ui.View:
        v = discord.ui.View(timeout=None)
        v.add_item(profile_link_button(roblox_user_id))
        return v

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._accept_flow(interaction)

    @discord.ui.button(label="Deny", style=discord.ButtonStyle.danger)
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._deny_flow(interaction)

    async def _accept_flow(self, interaction: discord.Interaction):
        member = interaction.user
        if not isinstance(member, discord.Member):
            await interaction.response.send_message("Use isso no servidor.", ephemeral=True)
            return

        session = get_session()
        try:
            tx = session.get(TransactionRequest, self.tx_id)
            if not tx or tx.status != "PENDING":
                await interaction.response.send_message("Transaction inválida.", ephemeral=True)
                return

            guild = interaction.guild
            target = guild.get_member(tx.target_user_id) if guild else None
            requester = guild.get_member(tx.requested_by) if guild else None
            to_team_name = _team_name(session, tx.to_team_id)

            # TRANSFER: 2 etapas
            if tx.action == "TRANSFER":
                # etapa 1: player aceita
                if not tx.player_confirmed:
                    if member.id != tx.target_user_id:
                        await interaction.response.send_message("Waiting for the player to accept first (0/2).", ephemeral=True)
                        return

                    tx.player_confirmed = True
                    tx.player_confirmed_by = member.id
                    tx.player_confirmed_at = datetime.utcnow()
                    session.commit()

                    emb, rbx_id = await build_pending_embed(
                        session,
                        tx=tx,
                        requester=requester or member,
                        target=target or member,
                        to_team_name=to_team_name,
                    )
                    view = TxReviewView(self.tx_id, rbx_id)
                    # muda label do Accept
                    for item in view.children:
                        if isinstance(item, discord.ui.Button) and item.style == discord.ButtonStyle.success:
                            item.label = "Accept (1/2)"
                    await interaction.response.edit_message(embed=emb, view=view)
                    return

                # etapa 2: Transaction Team finaliza
                if not can_review_transactions(member):
                    await interaction.response.send_message("Only Transaction Team can finalize the transfer (1/2).", ephemeral=True)
                    return

                await self._final_approve(interaction, session, tx, requester, target, to_team_name)
                return

            # ADD/REMOVE: só Transaction Team aprova
            if not can_review_transactions(member):
                await interaction.response.send_message("Sem permissão.", ephemeral=True)
                return

            await self._final_approve(interaction, session, tx, requester, target, to_team_name)

        finally:
            session.close()

    async def _final_approve(self, interaction, session, tx, requester, target, to_team_name):
        tx.status = "APPROVED"
        tx.reviewed_by = interaction.user.id
        tx.reviewed_at = datetime.utcnow()
        session.commit()

        # DB Player
        guild_id = tx.guild_id
        guild = interaction.guild

        # garante row
        if guild and target:
            player_row = await _ensure_player_row(session, guild_id, target)
        else:
            player_row = session.query(Player).filter_by(guild_id=guild_id, user_id=tx.target_user_id).first()
            if not player_row:
                player_row = Player(guild_id=guild_id, user_id=tx.target_user_id, username=tx.target_username)
                session.add(player_row)
                session.flush()

        # atualizar team_id
        if tx.action in ("ADD", "TRANSFER"):
            player_row.team_id = tx.to_team_id
        elif tx.action == "REMOVE":
            player_row.team_id = None
        session.commit()

        # roles no Discord (mantém tua lógica atual de roles, simples)
        if guild and target:
            # Descobre role do time
            team_role_id = None
            if tx.to_team_id:
                t = session.query(Team).filter_by(id=tx.to_team_id).first()
                if t:
                    team_role_id = t.role_id

            # limpa posição
            for rid in (CFG.ROLE_VICE_CAPTAIN_ID, CFG.ROLE_COURT_CAPTAIN_ID, CFG.ROLE_PLAYER_ID):
                r = guild.get_role(rid)
                if r:
                    await target.remove_roles(r, reason="League transaction cleanup")

            if tx.action == "REMOVE":
                if team_role_id:
                    tr = guild.get_role(team_role_id)
                    if tr:
                        await target.remove_roles(tr, reason="League remove approved")
            else:
                if team_role_id:
                    tr = guild.get_role(team_role_id)
                    if tr:
                        await target.add_roles(tr, reason="League add/transfer approved")

                if tx.action == "ADD" and tx.requested_role:
                    rr = guild.get_role(role_key_to_id(tx.requested_role))
                    if rr:
                        await target.add_roles(rr, reason="League role assigned on approve")

                if tx.action == "TRANSFER":
                    rr = guild.get_role(CFG.ROLE_PLAYER_ID)
                    if rr:
                        await target.add_roles(rr, reason="League transfer default role")

        emb, rbx_id = await build_result_embed(
            session,
            success=True,
            tx=tx,
            requester=requester or interaction.user,
            actor=interaction.user,
            target=target or interaction.user,
            to_team_name=to_team_name,
        )
        await interaction.response.edit_message(embed=emb, view=TxReviewView.profile_only(rbx_id))

    async def _deny_flow(self, interaction: discord.Interaction):
        member = interaction.user
        if not isinstance(member, discord.Member):
            await interaction.response.send_message("Use isso no servidor.", ephemeral=True)
            return

        session = get_session()
        try:
            tx = session.get(TransactionRequest, self.tx_id)
            if not tx or tx.status != "PENDING":
                await interaction.response.send_message("Transaction inválida.", ephemeral=True)
                return

            # TRANSFER: player pode negar imediatamente na etapa 0/2
            if tx.action == "TRANSFER" and member.id == tx.target_user_id and not tx.player_confirmed:
                tx.status = "REJECTED"
                tx.reason = "Player denied the transfer."
                tx.reviewed_by = member.id
                tx.reviewed_at = datetime.utcnow()
                session.commit()

                guild = interaction.guild
                target = guild.get_member(tx.target_user_id) if guild else None
                requester = guild.get_member(tx.requested_by) if guild else None
                to_team_name = _team_name(session, tx.to_team_id)

                emb, rbx_id = await build_result_embed(
                    session,
                    success=False,
                    tx=tx,
                    requester=requester or member,
                    actor=member,
                    target=target or member,
                    to_team_name=to_team_name,
                )
                await interaction.response.edit_message(embed=emb, view=TxReviewView.profile_only(rbx_id))
                return

            # Staff deny -> modal de motivo
            if not can_review_transactions(member):
                await interaction.response.send_message("Only Transaction Team can deny this transaction.", ephemeral=True)
                return

            await interaction.response.send_modal(DenyReasonModal(self.tx_id))

        finally:
            session.close()


# ----------------------------
# COG
# ----------------------------
class TransactionsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="team_add", description="Cadastra um time na liga (nome + role + captain).")
    @app_commands.describe(name="Nome do time", role="Cargo do time", captain="Capitão do time")
    async def team_add(self, interaction: discord.Interaction, name: str, role: discord.Role, captain: discord.Member):
        if not isinstance(interaction.user, discord.Member) or not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Só admin.", ephemeral=True)
            return

        session = get_session()
        try:
            if session.query(Team).filter_by(name=name).first():
                await interaction.response.send_message("Time já existe.", ephemeral=True)
                return

            t = Team(name=name, role_id=role.id, captain_user_id=captain.id)
            session.add(t)
            session.commit()

            # roles
            await captain.add_roles(role, reason="Team captain set on team_add")
            cap_global = interaction.guild.get_role(CFG.CAPTAIN_ROLE_ID) if (interaction.guild and CFG.CAPTAIN_ROLE_ID) else None
            if cap_global:
                await captain.add_roles(cap_global, reason="Captain role set on team_add")

            # DB register captain (pra achar time do captain depois)
            captain_row = await _ensure_player_row(session, interaction.guild_id or 0, captain)
            captain_row.team_id = t.id
            session.commit()

            await interaction.response.send_message(f"Time **{name}** cadastrado. Captain: {captain.mention}", ephemeral=True)
        finally:
            session.close()

    @app_commands.command(name="team_list", description="Lista os times cadastrados.")
    async def team_list(self, interaction: discord.Interaction):
        session = get_session()
        try:
            teams = session.query(Team).order_by(Team.name.asc()).all()
            if not teams:
                await interaction.response.send_message("Nenhum time cadastrado.", ephemeral=True)
                return
            txt = "\n".join([f"- **{t.name}**" for t in teams])
            await interaction.response.send_message(txt, ephemeral=True)
        finally:
            session.close()

    # ---- TRANSACTIONS (sem team_name)
    @app_commands.command(name="tr_add", description="Transaction: adicionar jogador no SEU time.")
    @app_commands.describe(player="Jogador", role="Role no time (Vice/Court/Player)")
    @app_commands.choices(role=[
        app_commands.Choice(name="Vice Captain", value="Vice Captain"),
        app_commands.Choice(name="Court Captain", value="Court Captain"),
        app_commands.Choice(name="Player", value="Player"),
    ])
    async def tr_add(self, interaction: discord.Interaction, player: discord.Member, role: app_commands.Choice[str]):
        await self._create_tx(interaction, action="ADD", player=player, requested_role=role.value)

    @app_commands.command(name="tr_remove", description="Transaction: remover jogador do SEU time (vira Free Agent).")
    @app_commands.describe(player="Jogador")
    async def tr_remove(self, interaction: discord.Interaction, player: discord.Member):
        await self._create_tx(interaction, action="REMOVE", player=player, requested_role="Player")

    @app_commands.command(name="tr_transfer", description="Transaction: transferir jogador para o SEU time (player must accept).")
    @app_commands.describe(player="Jogador")
    async def tr_transfer(self, interaction: discord.Interaction, player: discord.Member):
        await self._create_tx(interaction, action="TRANSFER", player=player, requested_role=None)

    async def _create_tx(
        self,
        interaction: discord.Interaction,
        action: str,
        player: discord.Member,
        requested_role: str | None,
    ):
        requester = interaction.user
        if not isinstance(requester, discord.Member):
            await interaction.response.send_message("Use no servidor.", ephemeral=True)
            return

        if not can_open_transactions(requester):
            await interaction.response.send_message("Apenas Captain/Vice Captain podem abrir transactions.", ephemeral=True)
            return

        guild_id = interaction.guild_id or 0

        session = get_session()
        try:
            # ✅ pega o time DO requester (DB -> fallback por roles)
            requester_team = await _get_requester_team(session, guild_id, requester)
            if not requester_team:
                await interaction.response.send_message(
                    "Não consegui identificar seu time. (Confere se seu time foi cadastrado com /team_add e se você tem o cargo do time.)",
                    ephemeral=True
                )
                return

            # alvo: garante row e tenta pegar team atual
            target_row = await _ensure_player_row(session, guild_id, player)
            target_current_team_id = target_row.team_id

            # Regras: remove só se o cara for do seu time
            if action == "REMOVE":
                if target_current_team_id != requester_team.id:
                    await interaction.response.send_message("Você só pode remover jogadores do SEU time.", ephemeral=True)
                    return

            # Regras: add só pro seu time
            if action == "ADD":
                # se já estiver em outro time, pode negar na staff com reason depois
                pass

            # Transfer: destino = seu time, from = inferido do DB
            from_team_id = target_current_team_id if action == "TRANSFER" else None
            to_team_id = requester_team.id if action in ("ADD", "TRANSFER") else None

            tx = TransactionRequest(
                guild_id=guild_id,
                requested_by=requester.id,
                target_user_id=player.id,
                target_username=str(player),
                action=action,
                from_team_id=from_team_id,
                to_team_id=to_team_id,
                requested_role=requested_role,
                status="PENDING",
                reason=None,
                player_confirmed=False,
                player_confirmed_by=None,
                player_confirmed_at=None,
            )
            session.add(tx)
            session.commit()

            to_team_name = requester_team.name if to_team_id else "Free Agent"

            emb, rbx_id = await build_pending_embed(
                session,
                tx=tx,
                requester=requester,
                target=player,
                to_team_name=to_team_name,
            )

            view = TxReviewView(tx.id, rbx_id)
            await interaction.response.send_message(embed=emb, view=view)

        finally:
            session.close()


async def setup(bot: commands.Bot):
    await bot.add_cog(TransactionsCog(bot))