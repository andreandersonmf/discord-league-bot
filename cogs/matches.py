from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
import random

from db.session import get_session
from db.models import MatchSchedule, MatchResult
from utils.checks import can_post_results
from utils.embeds import e_err, e_ok, e_info

def gen_match_id() -> str:
    # simples e único (pode trocar por algo mais “bonito”)
    return f"SA-{datetime.utcnow().strftime('%Y%m%d')}-{random.randint(1000,9999)}"

class MatchesCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="match_create", description="Cria um match na agenda (gera match_id).")
    @app_commands.describe(team_a="Time A", team_b="Time B", best_of="Bo (3 ou 5)", when="Data/hora (texto) opcional")
    async def match_create(self, interaction: discord.Interaction, team_a: str, team_b: str, best_of: int = 5, when: str | None = None):
        if not isinstance(interaction.user, discord.Member) or not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(embed=e_err("Sem permissão", "Só admin."), ephemeral=True)
            return

        session = get_session()
        try:
            mid = gen_match_id()
            ms = MatchSchedule(
                guild_id=interaction.guild_id or 0,
                match_id=mid,
                team_a=team_a,
                team_b=team_b,
                best_of=best_of,
                scheduled_at=None,
                status="OPEN",
            )
            session.add(ms)
            session.commit()

            emb = discord.Embed(title="Match criado", color=0x2ecc71)
            emb.add_field(name="Match ID", value=f"`{mid}`", inline=False)
            emb.add_field(name="Confronto", value=f"**{team_a}** vs **{team_b}** (Bo{best_of})", inline=False)
            emb.add_field(name="Quando", value=when or "—", inline=False)
            await interaction.response.send_message(embed=emb, ephemeral=False)
        finally:
            session.close()

    @app_commands.command(name="match_close", description="Fecha um match (por match_id).")
    @app_commands.describe(match_id="ID do match")
    async def match_close(self, interaction: discord.Interaction, match_id: str):
        if not isinstance(interaction.user, discord.Member) or not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(embed=e_err("Sem permissão", "Só admin."), ephemeral=True)
            return

        session = get_session()
        try:
            ms = session.query(MatchSchedule).filter_by(guild_id=interaction.guild_id, match_id=match_id).first()
            if not ms:
                await interaction.response.send_message(embed=e_err("Não achei", "Match ID inválido."), ephemeral=True)
                return
            ms.status = "CLOSED"
            session.commit()
            await interaction.response.send_message(embed=e_ok("OK", f"Match `{match_id}` foi fechado."), ephemeral=True)
        finally:
            session.close()

    @app_commands.command(name="result_post", description="Posta resultado do match (Referee/Media/Admin).")
    @app_commands.describe(match_id="ID do match", a="Placar Time A", b="Placar Time B", mvp_a="MVP do time A (opcional)", mvp_b="MVP do time B (opcional)")
    async def result_post(
        self,
        interaction: discord.Interaction,
        match_id: str,
        a: int,
        b: int,
        mvp_a: discord.Member | None = None,
        mvp_b: discord.Member | None = None
    ):
        member = interaction.user
        if not isinstance(member, discord.Member):
            await interaction.response.send_message(embed=e_err("Erro", "Use no servidor."), ephemeral=True)
            return

        if not can_post_results(member):
            await interaction.response.send_message(embed=e_err("Sem permissão", "Apenas Admin/Referee/Media."), ephemeral=True)
            return

        session = get_session()
        try:
            ms = session.query(MatchSchedule).filter_by(guild_id=interaction.guild_id, match_id=match_id).first()
            if not ms:
                await interaction.response.send_message(embed=e_err("Não achei", "Match ID inválido."), ephemeral=True)
                return

            # salva resultado
            r = MatchResult(
                guild_id=interaction.guild_id or 0,
                match_id=match_id,
                team_a_score=a,
                team_b_score=b,
                mvp_a=mvp_a.id if mvp_a else None,
                mvp_b=mvp_b.id if mvp_b else None,
                posted_by=interaction.user.id
            )
            session.add(r)

            ms.status = "DONE"
            session.commit()

            emb = discord.Embed(title="Resultado", color=0x2ecc71)
            emb.add_field(name="Match ID", value=f"`{match_id}`", inline=False)
            emb.add_field(name="Confronto", value=f"**{ms.team_a}** vs **{ms.team_b}**", inline=False)
            emb.add_field(name="Placar", value=f"**{a}** x **{b}**", inline=False)
            emb.add_field(name="MVP A", value=(mvp_a.mention if mvp_a else "—"), inline=True)
            emb.add_field(name="MVP B", value=(mvp_b.mention if mvp_b else "—"), inline=True)
            emb.set_footer(text=f"Postado por {interaction.user} • {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
            await interaction.response.send_message(embed=emb, ephemeral=False)
        finally:
            session.close()

    @app_commands.command(name="match_list", description="Lista matches abertos/fechados.")
    async def match_list(self, interaction: discord.Interaction):
        session = get_session()
        try:
            rows = session.query(MatchSchedule).filter_by(guild_id=interaction.guild_id).order_by(MatchSchedule.created_at.desc()).limit(10).all()
            if not rows:
                await interaction.response.send_message(embed=e_info("Vazio", "Nenhum match criado ainda."), ephemeral=True)
                return

            lines = []
            for m in rows:
                lines.append(f"`{m.match_id}` • **{m.team_a}** vs **{m.team_b}** • {m.status}")
            await interaction.response.send_message("\n".join(lines), ephemeral=True)
        finally:
            session.close()

async def setup(bot: commands.Bot):
    await bot.add_cog(MatchesCog(bot))