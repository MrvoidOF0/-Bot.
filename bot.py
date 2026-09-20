import discord
from discord.ext import commands
import asyncio
import logging
import os
import sys

from utils.config import Config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("CardsOfDoons")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.guilds = True


class CardsOfDoonsBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!cod_",
            intents=intents,
            help_command=None,
            application_id=None
        )

    async def setup_hook(self):
        logger.info("Carregando cogs...")

        cogs = [
            "cogs.welcome",
            "cogs.tickets",
            "cogs.commands",
            "cogs.support_ai",
            "cogs.painel_suporte",
        ]

        for cog in cogs:
            try:
                await self.load_extension(cog)
                logger.info(f"  ✅ {cog} carregado.")
            except Exception as e:
                logger.error(f"  ❌ Erro ao carregar {cog}: {e}")

        logger.info("Sincronizando slash commands...")
        try:
            synced = await self.tree.sync()
            logger.info(f"  ✅ {len(synced)} comando(s) sincronizado(s).")
        except Exception as e:
            logger.error(f"  ❌ Erro ao sincronizar comandos: {e}")

    async def on_ready(self):
        logger.info("─" * 50)
        logger.info(f"Bot online: {self.user} (ID: {self.user.id})")
        logger.info(f"Servidores: {len(self.guilds)}")
        logger.info("─" * 50)

        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.playing,
                name="Cards of Doons 🎴"
            ),
            status=discord.Status.online
        )

    async def on_disconnect(self):
        logger.warning("Bot desconectado. Tentando reconectar...")

    async def on_resumed(self):
        logger.info("Conexão retomada.")

    async def on_error(self, event: str, *args, **kwargs):
        logger.error(f"Erro no evento '{event}':", exc_info=True)


async def main():
    config = Config()

    if not config.DISCORD_TOKEN:
        logger.critical("DISCORD_TOKEN não definido. Verifique as variáveis de ambiente.")
        sys.exit(1)

    if not config.GROQ_API_KEY:
        logger.warning("GROQ_API_KEY não definida. A IA ficará indisponível.")

    bot = CardsOfDoonsBot()

    try:
        logger.info("Iniciando bot...")
        await bot.start(config.DISCORD_TOKEN)
    except discord.LoginFailure:
        logger.critical("Token inválido. Verifique DISCORD_TOKEN.")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Encerrando por solicitação do usuário.")
    except Exception as e:
        logger.critical(f"Erro fatal: {e}", exc_info=True)
        sys.exit(1)
    finally:
        if not bot.is_closed():
            await bot.close()
        logger.info("Bot encerrado.")


if __name__ == "__main__":
    asyncio.run(main())
