import discord
from config import CFG


def has_role(member: discord.Member, role_id: int) -> bool:
    return any(r.id == role_id for r in member.roles)


# --- Transactions: só Captain/Vice Captain (ou Admin) ---
def can_open_transactions(member: discord.Member) -> bool:
    if member.guild_permissions.administrator:
        return True

    if CFG.CAPTAIN_ROLE_ID and has_role(member, CFG.CAPTAIN_ROLE_ID):
        return True

    if has_role(member, CFG.VICE_CAPTAIN_ROLE_ID):
        return True

    return False


def can_review_transactions(member: discord.Member) -> bool:
    return can_open_transactions(member)


# --- Results: Admin / Referee / Media ---
def can_post_results(member: discord.Member) -> bool:
    if member.guild_permissions.administrator:
        return True

    return any(
        r.id in (CFG.REFEREE_ROLE_ID, CFG.MEDIA_ROLE_ID)
        for r in member.roles
    )