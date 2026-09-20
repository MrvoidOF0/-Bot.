import asyncio
import logging
import time
from typing import Optional

import discord
from discord.ext import commands

from cogs.tickets import active_tickets, ai_disabled_tickets
from services.groq_service import groq_service

logger = logging.getLogger("SupportAI")

# ─────────────────────────────────────────
# Armazenamento do contexto de cada ticket
# ─────────────────────────────────────────
# {channel_id: [{"role": "...", "content": "..."}]}
ticket_histories: dict[int, list] = {}

# ─────────────────────────────────────────
# Rate limit por usuário
# ─────────────────────────────────────────
# {user_id: last_message_timestamp}
user_last_message: dict[int, float] = {}

# Tempo mínimo entre mensagens (segundos)
RATE_LIMIT_SECONDS = 5.0

# Tempo mínimo para a IA responder após a última mensagem (debounce)
AI_DEBOUNCE_SECONDS = 1.5


class SupportAI(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Controle de debounce por canal: {channel_id: task}
        self._pending_tasks: dict[int, asyncio.Task] = {}

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Intercepta mensagens nos canais de ticket e aciona a IA."""

        # Ignora bots (incluindo o próprio bot)
        if message.author.bot:
            return

        # Ignora DMs
        if not message.guild:
            return

        channel = message.channel

        # Verifica se é um canal de ticket
        if not channel.name.startswith("ticket-"):
            return

        # Verifica se o ticket está registrado como ativo
        user_id = message.author.id
        if active_tickets.get(user_id) != channel.id:
            # Pode ser a staff escrevendo; ignora sem erro
            # Mas se o canal tem algum ticket ativo, ainda processa
            # Se não for o dono do ticket, ignora
            is_ticket_owner = any(cid == channel.id for cid in active_tickets.values())
            if not is_ticket_owner:
                return
            # Staff escrevendo — não ativa a IA
            # Verifica se quem escreveu é staff
            if isinstance(message.author, discord.Member):
                if message.author.guild_permissions.manage_guild or \
                   message.author.guild_permissions.administrator:
                    return

        # Verifica se a IA está desativada neste ticket
        if channel.id in ai_disabled_tickets:
            return

        # ─── Rate limit ───
        now = time.monotonic()
        last = user_last_message.get(user_id, 0)
        elapsed = now - last

        if elapsed < RATE_LIMIT_SECONDS:
            remaining = round(RATE_LIMIT_SECONDS - elapsed, 1)
            try:
                await channel.send(
                    f"⏳ {message.author.mention}, aguarde **{remaining}s** antes de enviar outra mensagem.",
                    delete_after=5
                )
            except (discord.Forbidden, discord.HTTPException):
                pass
            return

        user_last_message[user_id] = now

        # ─── Debounce ───
        # Cancela tarefa pendente se existir (aguarda o usuário parar de digitar)
        if channel.id in self._pending_tasks:
            self._pending_tasks[channel.id].cancel()

        task = asyncio.create_task(
            self._process_ai_response(message, channel)
        )
        self._pending_tasks[channel.id] = task

    async def _process_ai_response(
        self,
        message: discord.Message,
        channel: discord.TextChannel
    ):
        """Processa a resposta da IA com debounce."""
        try:
            await asyncio.sleep(AI_DEBOUNCE_SECONDS)

            # Verifica novamente se a IA ainda está ativa
            if channel.id in ai_disabled_tickets:
                return

            # Recupera ou inicializa o histórico do ticket
            history = ticket_histories.get(channel.id, [])

            # Envia indicador de digitação
            async with channel.typing():
                ai_response, updated_history = await groq_service.chat(
                    user_message=message.content,
                    history=history
                )

            # Atualiza o histórico
            ticket_histories[channel.id] = updated_history

            # Envia a resposta
            # Divide respostas longas em múltiplas mensagens
            if len(ai_response) <= 2000:
                try:
                    await channel.send(f"🤖 {ai_response}")
                except (discord.Forbidden, discord.HTTPException) as e:
                    logger.error(f"Erro ao enviar resposta da IA no canal {channel.id}: {e}")
            else:
                # Divide a resposta em blocos de 1900 caracteres
                chunks = [ai_response[i:i+1900] for i in range(0, len(ai_response), 1900)]
                for i, chunk in enumerate(chunks):
                    prefix = "🤖 " if i == 0 else ""
                    try:
                        await channel.send(f"{prefix}{chunk}")
                    except (discord.Forbidden, discord.HTTPException) as e:
                        logger.error(f"Erro ao enviar chunk da IA: {e}")
                        break

            logger.info(
                f"IA respondeu no ticket {channel.name} para {message.author}. "
                f"Histórico: {len(updated_history)} mensagens."
            )

        except asyncio.CancelledError:
            # Tarefa cancelada pelo debounce — normal
            pass
        except Exception as e:
            logger.error(f"Erro inesperado no _process_ai_response: {e}", exc_info=True)
            try:
                await channel.send(
                    "⚠️ O atendimento automático encontrou um erro inesperado. "
                    "Aguarde um membro da equipe."
                )
            except (discord.Forbidden, discord.HTTPException):
                pass
        finally:
            # Remove a tarefa do registro
            if channel.id in self._pending_tasks:
                del self._pending_tasks[channel.id]


def clear_ticket_history(channel_id: int):
    """Remove o histórico de um ticket quando ele é fechado."""
    if channel_id in ticket_histories:
        del ticket_histories[channel_id]
        logger.info(f"Histórico do ticket {channel_id} limpo.")


async def setup(bot: commands.Bot):
    await bot.add_cog(SupportAI(bot))
