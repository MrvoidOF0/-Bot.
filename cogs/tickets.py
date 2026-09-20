import logging
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from utils.config import config
from utils.permissions import is_staff, is_staff_interaction

logger = logging.getLogger("Tickets")

# ─────────────────────────────────────────
# Armazenamento em memória dos tickets ativos
# ─────────────────────────────────────────
# Estrutura: {user_id: channel_id}
active_tickets: dict[int, int] = {}

# Tickets com IA desativada (staff assumiu): {channel_id: True}
ai_disabled_tickets: set[int] = set()


# ─────────────────────────────────────────
# Views
# ─────────────────────────────────────────

class SetupTicketView(discord.ui.View):
    """View do painel de abertura de tickets."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🎫 Abrir Ticket",
        style=discord.ButtonStyle.primary,
        custom_id="open_ticket_button"
    )
    async def open_ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await handle_open_ticket(interaction)


class TicketActionsView(discord.ui.View):
    """View com botões dentro do ticket."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🔒 Fechar Ticket",
        style=discord.ButtonStyle.danger,
        custom_id="close_ticket_button"
    )
    async def close_ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await handle_close_ticket_request(interaction)

    @discord.ui.button(
        label="🛡️ Chamar Staff",
        style=discord.ButtonStyle.secondary,
        custom_id="call_staff_button"
    )
    async def call_staff(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await handle_call_staff(interaction)


class ConfirmCloseView(discord.ui.View):
    """View de confirmação para fechar o ticket."""

    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.button(
        label="✅ Confirmar Fechamento",
        style=discord.ButtonStyle.danger,
        custom_id="confirm_close_button"
    )
    async def confirm_close(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await handle_close_ticket_confirmed(interaction)

    @discord.ui.button(
        label="❌ Cancelar",
        style=discord.ButtonStyle.secondary,
        custom_id="cancel_close_button"
    )
    async def cancel_close(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.edit_message(
            content="✅ Fechamento cancelado. O ticket permanece aberto.",
            view=None
        )


class ReactivateAIView(discord.ui.View):
    """View para reativar a IA após staff assumir."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🤖 Reativar IA",
        style=discord.ButtonStyle.success,
        custom_id="reactivate_ai_button"
    )
    async def reactivate_ai(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if not is_staff_interaction(interaction):
            await interaction.response.send_message(
                "❌ Apenas a equipe pode reativar a IA.",
                ephemeral=True
            )
            return

        channel_id = interaction.channel_id
        if channel_id in ai_disabled_tickets:
            ai_disabled_tickets.discard(channel_id)
            await interaction.response.send_message(
                "🤖 A IA de suporte foi **reativada** neste ticket e voltará a responder automaticamente.",
                ephemeral=False
            )
            logger.info(f"IA reativada no ticket {channel_id} por {interaction.user}.")
        else:
            await interaction.response.send_message(
                "ℹ️ A IA já está ativa neste ticket.",
                ephemeral=True
            )


# ─────────────────────────────────────────
# Handlers
# ─────────────────────────────────────────

async def handle_open_ticket(interaction: discord.Interaction):
    """Cria um novo ticket para o usuário."""
    user = interaction.user
    guild = interaction.guild

    # Verifica se já possui ticket aberto
    if user.id in active_tickets:
        existing_channel_id = active_tickets[user.id]
        existing_channel = guild.get_channel(existing_channel_id)
        if existing_channel:
            await interaction.response.send_message(
                f"❌ Você já possui um ticket aberto: {existing_channel.mention}\n"
                "Utilize o ticket existente para continuar o atendimento.",
                ephemeral=True
            )
            return
        else:
            # Canal não existe mais, remove do registro
            del active_tickets[user.id]

    # Busca a categoria dos tickets
    category = guild.get_channel(config.TICKET_CATEGORY_ID)
    if category is None or not isinstance(category, discord.CategoryChannel):
        await interaction.response.send_message(
            "❌ A categoria de tickets não foi encontrada. Contate um administrador.",
            ephemeral=True
        )
        logger.error(
            f"Categoria de tickets não encontrada (ID: {config.TICKET_CATEGORY_ID})."
        )
        return

    await interaction.response.defer(ephemeral=True)

    # Define as permissões do canal
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(
            view_channel=False,
            send_messages=False,
            read_messages=False
        ),
        user: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_messages=True,
            read_message_history=True
        ),
        guild.me: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_messages=True,
            read_message_history=True,
            manage_channels=True,
            manage_messages=True
        ),
    }

    # Adiciona permissões para staff (roles com manage_guild)
    for role in guild.roles:
        if role.permissions.manage_guild or role.permissions.administrator:
            overwrites[role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_messages=True,
                read_message_history=True
            )

    # Sanitiza o nome do canal
    safe_name = "".join(
        c if c.isalnum() or c in "-_" else "-"
        for c in user.display_name.lower()
    ).strip("-")[:20]

    channel_name = f"ticket-{safe_name}"

    try:
        ticket_channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites,
            topic=f"Ticket de {user} (ID: {user.id})"
        )
    except discord.Forbidden:
        await interaction.followup.send(
            "❌ Sem permissão para criar o canal de ticket. Contate um administrador.",
            ephemeral=True
        )
        return
    except discord.HTTPException as e:
        await interaction.followup.send(
            f"❌ Erro ao criar o ticket: {e}",
            ephemeral=True
        )
        return

    # Registra o ticket
    active_tickets[user.id] = ticket_channel.id
    logger.info(f"Ticket criado: {ticket_channel.name} para {user}.")

    # Envia a mensagem inicial no ticket
    embed = discord.Embed(
        title="🎫 Atendimento — Cards of Doons",
        description=(
            f"Olá, {user.mention}!\n\n"
            "Explique seu **problema** ou **dúvida** com o máximo de detalhes possível.\n\n"
            "🤖 Um atendente virtual irá ajudar com sua solicitação.\n"
            "🛡️ Você também pode solicitar atendimento direto da equipe.\n\n"
            "⚠️ **Nunca envie senhas, tokens ou informações pessoais.**"
        ),
        color=discord.Color.from_rgb(138, 43, 226),
    )
    embed.set_footer(text="Cards of Doons | Suporte")

    await ticket_channel.send(
        content=user.mention,
        embed=embed,
        view=TicketActionsView()
    )

    await interaction.followup.send(
        f"✅ Seu ticket foi criado: {ticket_channel.mention}",
        ephemeral=True
    )

    # Log
    await send_log(
        guild=guild,
        bot=interaction.client,
        description=f"🎫 **Ticket aberto** por {user.mention}\nCanal: {ticket_channel.mention}",
        color=discord.Color.green()
    )


async def handle_close_ticket_request(interaction: discord.Interaction):
    """Pede confirmação antes de fechar o ticket."""
    channel = interaction.channel

    # Verifica se é um canal de ticket válido
    if not channel.name.startswith("ticket-"):
        await interaction.response.send_message(
            "❌ Este comando só pode ser usado dentro de um ticket.",
            ephemeral=True
        )
        return

    await interaction.response.send_message(
        "⚠️ Tem certeza que deseja **fechar** este ticket?\n"
        "Esta ação encerrará o atendimento e o canal será deletado.",
        view=ConfirmCloseView(),
        ephemeral=True
    )


async def handle_close_ticket_confirmed(interaction: discord.Interaction):
    """Fecha e deleta o canal de ticket."""
    channel = interaction.channel
    guild = interaction.guild
    closer = interaction.user

    # Encontra o dono do ticket
    owner_id = None
    for uid, cid in list(active_tickets.items()):
        if cid == channel.id:
            owner_id = uid
            break

    await interaction.response.edit_message(
        content="🔒 Fechando o ticket...",
        view=None
    )

    # Envia mensagem final
    close_embed = discord.Embed(
        title="🔒 Ticket Fechado",
        description=f"Este ticket foi fechado por {closer.mention}.\nO canal será deletado em instantes.",
        color=discord.Color.red()
    )
    await channel.send(embed=close_embed)

    # Remove do registro
    if owner_id and owner_id in active_tickets:
        del active_tickets[owner_id]

    if channel.id in ai_disabled_tickets:
        ai_disabled_tickets.discard(channel.id)

    logger.info(f"Ticket {channel.name} fechado por {closer}.")

    # Log
    await send_log(
        guild=guild,
        bot=interaction.client,
        description=f"🔒 **Ticket fechado** por {closer.mention}\nCanal: `{channel.name}`",
        color=discord.Color.red()
    )

    import asyncio
    await asyncio.sleep(3)

    try:
        await channel.delete(reason=f"Ticket fechado por {closer}")
    except discord.Forbidden:
        logger.error(f"Sem permissão para deletar o canal {channel.name}.")
    except discord.HTTPException as e:
        logger.error(f"Erro ao deletar canal {channel.name}: {e}")


async def handle_call_staff(interaction: discord.Interaction):
    """Notifica a equipe e desativa a IA no ticket."""
    channel = interaction.channel
    guild = interaction.guild
    user = interaction.user

    if not channel.name.startswith("ticket-"):
        await interaction.response.send_message(
            "❌ Este comando só pode ser usado dentro de um ticket.",
            ephemeral=True
        )
        return

    # Desativa a IA neste ticket
    ai_disabled_tickets.add(channel.id)

    # Monta a menção de staff
    staff_mention = ""
    for role in guild.roles:
        if role.permissions.manage_guild or role.permissions.administrator:
            staff_mention = role.mention
            break

    embed = discord.Embed(
        title="🛡️ Atendimento Humano Solicitado",
        description=(
            f"{user.mention} solicitou atendimento de um membro da equipe.\n\n"
            "🤖 A IA de suporte foi **desativada** neste ticket.\n"
            "Um membro da equipe irá atender em breve."
        ),
        color=discord.Color.orange()
    )

    await interaction.response.send_message(
        content=f"{staff_mention} — Atendimento solicitado!" if staff_mention else "🛡️ Atendimento solicitado!",
        embed=embed,
        view=ReactivateAIView()
    )

    logger.info(f"Staff chamado no ticket {channel.name} por {user}.")

    # Log
    await send_log(
        guild=guild,
        bot=interaction.client,
        description=f"🛡️ **Staff chamado** por {user.mention}\nCanal: {channel.mention}",
        color=discord.Color.orange()
    )


async def send_log(
    guild: discord.Guild,
    bot: commands.Bot,
    description: str,
    color: discord.Color
):
    """Envia uma mensagem no canal de logs, se configurado."""
    if not config.LOG_CHANNEL_ID:
        return

    log_channel = bot.get_channel(config.LOG_CHANNEL_ID)
    if log_channel is None:
        return

    embed = discord.Embed(
        description=description,
        color=color
    )
    embed.set_footer(text="Cards of Doons | Log")

    try:
        await log_channel.send(embed=embed)
    except (discord.Forbidden, discord.HTTPException):
        pass


# ─────────────────────────────────────────
# Cog
# ─────────────────────────────────────────

class Tickets(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        # Registra as views persistentes para sobreviver a reinicializações
        self.bot.add_view(SetupTicketView())
        self.bot.add_view(TicketActionsView())
        self.bot.add_view(ConfirmCloseView())
        self.bot.add_view(ReactivateAIView())

    @app_commands.command(
        name="setup_ticket",
        description="[STAFF] Envia o painel de abertura de tickets."
    )
    async def setup_ticket(self, interaction: discord.Interaction):
        """Envia o painel de suporte. Apenas staff."""
        if not is_staff_interaction(interaction):
            await interaction.response.send_message(
                "❌ Você não tem permissão para usar este comando.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="🎫 SUPORTE — CARDS OF DOONS",
            description=(
                "Precisa de ajuda? Abra um ticket e explique seu problema para receber atendimento.\n\n"
                "🤖 O atendimento automático poderá ajudar com dúvidas comuns.\n"
                "🛡️ Caso necessário, a equipe poderá assumir o atendimento.\n\n"
                "Clique no botão abaixo para abrir seu ticket."
            ),
            color=discord.Color.from_rgb(138, 43, 226),
        )

        if interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)

        embed.set_footer(text="Cards of Doons | Suporte • Um ticket por usuário")

        await interaction.response.send_message(
            embed=embed,
            view=SetupTicketView()
        )

        logger.info(f"{interaction.user} executou /setup_ticket em {interaction.channel}.")


async def setup(bot: commands.Bot):
    await bot.add_cog(Tickets(bot))
