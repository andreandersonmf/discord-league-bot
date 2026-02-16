import discord
from discord import app_commands
from discord.ext import commands

from db.session import get_session
from db.models import Team, Player
from utils.embeds import e_err, e_info

class RosterCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="roster", description="Mostra o roster de um time.")
    @app_commands.describe(team_name="Nome do time")
    async def roster(self, interaction: discord.Interaction, team_name: str):
        session = get_session()
        try:
            team = session.query(Team).filter(Team.name.ilike(team_name)).first()
            if not team:
                await interaction.response.send_message(embed=e_err("Não achei", f"Time **{team_name}** não cadastrado."), ephemeral=True)
                return

            players = session.query(Player).filter_by(guild_id=interaction.guild_id, team_id=team.id).order_by(Player.username.asc()).all()
            if not players:
                await interaction.response.send_message(embed=e_info("Roster", f"**{team.name}** ainda não tem jogadores."), ephemeral=True)
                return

            lines = [f"- <@{p.user_id}> ({p.username})" for p in players]
            emb = discord.Embed(title=f"Roster • {team.name}", description="\n".join(lines), color=0x2ecc71)
            await interaction.response.send_message(embed=emb, ephemeral=False)
        finally:
            session.close()

    @app_commands.command(name="player", description="Mostra info do jogador na liga.")
    async def player(self, interaction: discord.Interaction, user: discord.Member):
        session = get_session()
        try:
            p = session.query(Player).filter_by(guild_id=interaction.guild_id, user_id=user.id).first()
            if not p:
                await interaction.response.send_message(embed=e_err("Não registrado", "Esse jogador não está no banco ainda."), ephemeral=True)
                return

            team_name = "Free Agent"
            if p.team_id:
                t = session.query(Team).filter_by(id=p.team_id).first()
                if t:
                    team_name = t.name

            emb = discord.Embed(title="Player", color=0x3498db)
            emb.add_field(name="Jogador", value=f"{user.mention} ({p.username})", inline=False)
            emb.add_field(name="Time", value=team_name, inline=False)
            await interaction.response.send_message(embed=emb, ephemeral=True)
        finally:
            session.close()

async def setup(bot: commands.Bot):
    await bot.add_cog(RosterCog(bot))