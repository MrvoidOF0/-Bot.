import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Carrega e valida todas as variáveis de ambiente do bot."""

    def __init__(self):
        self.DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")
        self.GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
        self.GROQ_MODEL: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

        # IDs como inteiros
        self.WELCOME_CHANNEL_ID: int = self._parse_int("WELCOME_CHANNEL_ID", 1551208522253869127)
        self.TICKET_CATEGORY_ID: int = self._parse_int("TICKET_CATEGORY_ID", 1551209564815228988)
        self.LOG_CHANNEL_ID: int = self._parse_int("LOG_CHANNEL_ID", 0)

    @staticmethod
    def _parse_int(key: str, default: int) -> int:
        value = os.getenv(key, "")
        if value.strip().isdigit():
            return int(value.strip())
        return default


# Instância global
config = Config()
