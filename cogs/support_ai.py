import asyncio
import logging
import time

import discord
from discord.ext import commands

from cogs.tickets import active_tickets, ai_disabled_tickets
from services.groq_service import groq_service

logger = logging.getLogger("SupportAI")

# ─────────────────────────────────────────
# Contexto isolado por ticket
# ─────────────────────────────────────────
# {channel_id: [{"role": "...", "content": "..."}]}
ticket_histories: dict[int, list] = {}

# ─────────────────────────────────────────
# Rate limit por usuário
# ─────────────────────────────────────────
# {user_id: timestamp_da_ultima_mensagem}
user_last_message: dict[int, float] = {}

RATE_LIMIT_SECONDS = 5.0

# Debounce: aguarda o usuário parar de digitar antes de acionar a IA
AI_DEBOUNCE_SECONDS = 1.5


class SupportAI(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Controle de tarefas pendentes por canal: {channel_id: asyncio.Task}
        self._pending_tasks: dict[int, asyncio.Task] = {}

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Intercepta mensagens nos canais de ticket e aciona a IA."""

        # Ignora mensagens de bots (incluindo o próprio bot)
        if message.author.bot:
            return

        # Ignora DMs
        if not message.guild:
            return

        channel = message.channel

        # ── Verifica se é canal de ticket ──
        if not isinstance(channel, discord.TextChannel):
            return

        if not channel.name.startswith("ticket-"):
            return

        # ── Verifica se o canal está registrado como ticket ativo ──
        is_registered_ticket = any(
            cid == channel.id for cid in active_tickets.values()
        )
        if not is_registered_ticket:
            return

        # ── Se for staff escrevendo, não aciona a IA ──
        if isinstance(message.author, discord.Member):
            member = message.author
            if (
                member.guild_permissions.manage_guild
                or member.guild_permissions.administrator
                or member.guild_permissions.manage_channels
            ):
                return

        # ── Verifica se a IA está desativada neste ticket ──
        if channel.id in ai_disabled_tickets:
            return

        # ── Rate limit por usuário ──
        user_id = message.author.id
        now = time.monotonic()
        last = user_last_message.get(user_id, 0.0)
        elapsed = now - last

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

        # Registra o timestamp desta mensagem
        user_last_message[user_id] = now

        # ── Debounce: cancela tarefa anterior e agenda nova ──
        existing_task = self._pending_tasks.get(channel.id)
        if existing_task and not existing_task.done():
            existing_task.cancel()

        task = asyncio.create_task(
            self._process_ai_response(message, channel)
        )
        self._pending_tasks[channel.id] = task

    async def _process_ai_response(
        self,
        message: discord.Message,
        channel: discord.TextChannel
    ):
        """Aguarda o debounce e processa a resposta da IA."""
        try:
            # Aguarda o debounce antes de responder
            await asyncio.sleep(AI_DEBOUNCE_SECONDS)

            # Revalida se a IA ainda está ativa após o debounce
            if channel.id in ai_disabled_tickets:
                return

            # Recupera ou inicializa o histórico isolado deste ticket
            history = ticket_histories.get(channel.id, [])

            # Envia indicador de digitação enquanto processa
            async with channel.typing():
                ai_response, updated_history = await groq_service.chat(
                    user_message=message.content,
                    history=history
                )

            # Persiste o histórico atualizado
            ticket_histories[channel.id] = updated_history

            # ── Envia a resposta sem nenhum prefixo ──
            if not ai_response:
                return

            if len(ai_response) <= 2000:
                try:
                    await channel.send(ai_response)
                except (discord.Forbidden, discord.HTTPException) as e:
                    logger.error(
                        f"Erro ao enviar resposta da IA no canal {channel.id}: {e}"
                    )
            else:
                # Divide respostas longas em blocos de 1900 caracteres
                chunks = [
                    ai_response[i:i + 1900]
                    for i in range(0, len(ai_response), 1900)
                ]
                for chunk in chunks:
                    try:
                        await channel.send(chunk)
                    except (discord.Forbidden, discord.HTTPException) as e:
                        logger.error(f"Erro ao enviar chunk da IA: {e}")
                        break

            logger.info(
                f"IA respondeu em #{channel.name} para {message.author}. "
                f"Histórico: {len(updated_history)} mensagens."
            )

        except asyncio.CancelledError:
            # Cancelado pelo debounce — comportamento esperado
            pass

        except Exception as e:
            logger.error(
                f"Erro inesperado em _process_ai_response: {e}",
                exc_info=True
            )
            try:
                await channel.send(
                    "⚠️ O atendimento automático encontrou um erro inesperado. "
                    "Aguarde um membro da equipe."
                )
            except (discord.Forbidden, discord.HTTPException):
                pass

        finally:
            # Limpa a tarefa do registro ao finalizar
            self._pending_tasks.pop(channel.id, None)


def clear_ticket_history(channel_id: int):
    """Remove o histórico de conversa de um ticket encerrado."""
    if channel_id in ticket_histories:
        del ticket_histories[channel_id]
        logger.info(f"Histórico do ticket #{channel_id} removido da memória.")


async def setup(bot: commands.Bot):
    await bot.add_cog(SupportAI(bot))
