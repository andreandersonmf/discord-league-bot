import discord
from datetime import datetime

GREEN = 0x2ecc71
RED = 0xe74c3c
GRAY = 0x95a5a6
BLUE = 0x3498db

def e_info(title: str, desc: str) -> discord.Embed:
    return discord.Embed(title=title, description=desc, color=BLUE)

def e_ok(title: str, desc: str) -> discord.Embed:
    return discord.Embed(title=title, description=desc, color=GREEN)

def e_err(title: str, desc: str) -> discord.Embed:
    return discord.Embed(title=title, description=desc, color=RED)

def e_tx(title: str, fields: dict[str, str], status: str) -> discord.Embed:
    color = GRAY
    if status == "APPROVED":
        color = GREEN
    elif status == "REJECTED":
        color = RED

    emb = discord.Embed(title=title, color=color)
    for k, v in fields.items():
        emb.add_field(name=k, value=v, inline=False)
    emb.set_footer(text=f"Status: {status} • {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    return emb