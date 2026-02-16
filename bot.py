import discord
from discord.ext import commands

from config import CFG, must_token
from db import init_db

INTENTS = discord.Intents.default()
INTENTS.members = True

bot = commands.Bot(command_prefix="!", intents=INTENTS)

COGS = (
    "cogs.transactions",
    "cogs.roster",
    "cogs.matches",
)

@bot.event
async def on_ready():
    init_db()

    # carrega cogs
    for ext in COGS:
        if ext not in bot.extensions:
            await bot.load_extension(ext)

    # sincroniza slash commands no servidor (mais rápido)
    if CFG.GUILD_ID:
        guild = discord.Object(id=CFG.GUILD_ID)
        bot.tree.copy_global_to(guild=guild)
        synced = await bot.tree.sync(guild=guild)
        print(f"✅ Slash commands sincronizados no guild: {len(synced)}")
    else:
        synced = await bot.tree.sync()
        print(f"✅ Slash commands sincronizados global: {len(synced)}")

    print(f"🤖 Logado como {bot.user}")

def main():
    bot.run(must_token())

if __name__ == "__main__":
    main()