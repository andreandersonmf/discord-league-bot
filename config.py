from dataclasses import dataclass
import os
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Config:
    DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")

    GUILD_ID=1468750429012754464

    TRANSACTION_PERM_ROLE_ID=1472738473684238477
    REFEREE_ROLE_ID=1469045920199872794
    MEDIA_ROLE_ID=1469046014068523048

        # Permissões para abrir transações
    CAPTAIN_ROLE_ID=1469045798271582268
    VICE_CAPTAIN_ROLE_ID=1469045828139225266  # Vice Captain (global)

    ROLE_VICE_CAPTAIN_ID=1469045828139225266
    ROLE_COURT_CAPTAIN_ID=1472783263314612335
    ROLE_PLAYER_ID=1469045765182722151

    TRANSACTIONS_CHANNEL_ID=1472738799825195088

    DB_URL: str = "sqlite:///cvr_sa_bot.db"

CFG = Config()

def must_token() -> str:
    if not CFG.DISCORD_TOKEN:
        raise RuntimeError("DISCORD_TOKEN não configurado no .env")
    return CFG.DISCORD_TOKEN