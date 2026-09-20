import asyncio
import logging
import time

import discord
from discord.ext import commands

from services.groq_service import groq_service
from utils.state import active_tickets, ai_disabled_tickets

logger = logging.getLogger("SupportAI")

# {channel_id: [{"role": ..., "content": ...}]}
ticket_histories: dict[int, list] = {}

# {user_id: timestamp}
user_last_message: dict[int, float] = {}

RATE_LIMIT_SECONDS = 5.0
AI_DEBOUNCE_SECONDS = 1.5


class SupportAI(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._pending_tasks: dict[int, asyncio.Task] = {}

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        if not message.guild:
            return

        channel = message.channel

        if not isinstance(channel, discord.TextChannel):
            return

        if not channel.name.startswith("ticket-"):
            return

        is_registered = any(cid == channel.id for cid in active_tickets.values())
        if not is_registered:
            return

        if isinstance(message.author, discord.Member):
            member = message.author
            if (
                member.guild_permissions.manage_guild
                or member.guild_permissions.administrator
                or member.guild_permissions.manage_channels
            ):
                return

        if channel.id in ai_disabled_tickets:
            return

        user_id = message.author.id
        now = time.monotonic()
        elapsed = now - user_last_message.get(user_id, 0.0)

        if elapsed < RATE_LIMIT_SECONDS:
            remaining = round(RATE_LIMIT_SECONDS - elapsed, 1)
            try:
                await channel.send(
                    f"⏳ {message.author.mention}, aguarde **{remaining}s** "
                    "antes de enviar outra mensagem.",
                    delete_after=6
                )
            except (discord.Forbidden, discord.HTTPException):
                pass
            return

        user_last_message[user_id] = now

        existing = self._pending_tasks.get(channel.id)
        if existing and not existing.done():
            existing.cancel()

        task = asyncio.create_task(
            self._process_ai_response(message, channel)
        )
        self._pending_tasks[channel.id] = task

    async def _process_ai_response(
        self,
        message: discord.Message,
        channel: discord.TextChannel
    ):
        try:
            await asyncio.sleep(AI_DEBOUNCE_SECONDS)

            if channel.id in ai_disabled_tickets:
                return

            history = ticket_histories.get(channel.id, [])

            async with channel.typing():
                ai_response, updated_history = await groq_service.chat(
                    user_message=message.content,
                    history=history
                )

            ticket_histories[channel.id] = updated_history

            if not ai_response:
                return

            chunks = [
                ai_response[i:i + 1990]
                for i in range(0, len(ai_response), 1990)
            ]

            for chunk in chunks:
                try:
                    await channel.send(chunk)
                except (discord.Forbidden, discord.HTTPException) as e:
                    logger.error(f"Erro ao enviar resposta da IA: {e}")
                    break

            logger.info(
                f"IA respondeu em #{channel.name} para {message.author}. "
                f"Histórico: {len(updated_history)} msgs."
            )

        except asyncio.CancelledError:
            pass

        except Exception as e:
            logger.error(
                f"Erro em _process_ai_response: {e}",
                exc_info=True
            )
            try:
                await channel.send(
                    "⚠️ O atendimento automático encontrou um erro. "
                    "Aguarde um membro da equipe."
                )
            except (discord.Forbidden, discord.HTTPException):
                pass

        finally:
            self._pending_tasks.pop(channel.id, None)


async def setup(bot: commands.Bot):
    await bot.add_cog(SupportAI(bot))
    logger.info("Cog SupportAI carregado com sucesso.")
