import asyncio
import logging

import discord
from discord import app_commands
from discord.ext import commands

from utils.config import config
from utils.permissions import is_staff_interaction
from utils.state import active_tickets, ai_disabled_tickets

logger = logging.getLogger("Tickets")

EMBED_COLOR = discord.Color(0xe03f3f)


# ─────────────────────────────────────────
# Views
# ─────────────────────────────────────────

class SetupTicketView(discord.ui.View):
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
            embed = discord.Embed(
                description=(
                    "🤖 A IA foi **reativada** neste ticket e voltará "
                    "a responder automaticamente."
                ),
                color=EMBED_COLOR
            )
            await interaction.response.send_message(embed=embed)
            logger.info(
                f"IA reativada no ticket {channel_id} por {interaction.user}."
            )
        else:
            await interaction.response.send_message(
                "ℹ️ A IA já está ativa neste ticket.",
                ephemeral=True
            )


# ─────────────────────────────────────────
# Handlers
# ─────────────────────────────────────────

async def handle_open_ticket(interaction: discord.Interaction):
    user = interaction.user
    guild = interaction.guild

    if user.id in active_tickets:
        existing_channel = guild.get_channel(active_tickets[user.id])
        if existing_channel:
            await interaction.response.send_message(
                f"❌ Você já possui um ticket aberto: {existing_channel.mention}\n"
                "Utilize o ticket existente para continuar.",
                ephemeral=True
            )
            return
        else:
            del active_tickets[user.id]

    category = guild.get_channel(config.TICKET_CATEGORY_ID)
    if category is None or not isinstance(category, discord.CategoryChannel):
        await interaction.response.send_message(
            "❌ Categoria de tickets não encontrada. Contate um administrador.",
            ephemeral=True
        )
        logger.error(
            f"Categoria não encontrada (ID: {config.TICKET_CATEGORY_ID})."
        )
        return

    await interaction.response.defer(ephemeral=True)

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
            read_message_history=True,
            attach_files=True
        ),
        guild.me: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_messages=True,
            read_message_history=True,
            manage_channels=True,
            manage_messages=True,
            embed_links=True
        ),
    }

    for role in guild.roles:
        if role.permissions.manage_guild or role.permissions.administrator:
            if not role.is_bot_managed() and not role.is_integration():
                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_messages=True,
                    read_message_history=True,
                    manage_messages=True
                )

    safe_name = "".join(
        c if c.isalnum() or c in "-_" else "-"
        for c in user.display_name.lower()
    ).strip("-")[:20] or str(user.id)[:10]

    try:
        ticket_channel = await guild.create_text_channel(
            name=f"ticket-{safe_name}",
            category=category,
            overwrites=overwrites,
            topic=f"Ticket de {user} (ID: {user.id})"
        )
    except discord.Forbidden:
        await interaction.followup.send(
            "❌ Sem permissão para criar o canal. Contate um administrador.",
            ephemeral=True
        )
        return
    except discord.HTTPException as e:
        await interaction.followup.send(
            f"❌ Erro ao criar o ticket: {e}",
            ephemeral=True
        )
        return

    active_tickets[user.id] = ticket_channel.id
    logger.info(
        f"Ticket criado: #{ticket_channel.name} para {user} (ID: {user.id})."
    )

    embed = discord.Embed(
        title="🎫 Atendimento — Cards of Doons",
        description=(
            f"Olá, {user.mention}!\n\n"
            "Explique seu **problema** ou **dúvida** com detalhes.\n\n"
            "🤖 Um atendente virtual irá responder automaticamente.\n"
            "🛡️ Você também pode solicitar atendimento da equipe.\n\n"
            "⚠️ **Nunca envie senhas, tokens ou informações pessoais.**"
        ),
        color=EMBED_COLOR,
    )
    embed.set_footer(text="Cards of Doons | Suporte")

    await ticket_channel.send(
        content=user.mention,
        embed=embed,
        view=TicketActionsView()
    )

    await interaction.followup.send(
        f"✅ Ticket criado: {ticket_channel.mention}",
        ephemeral=True
    )

    await _send_log(
        guild=guild,
        bot=interaction.client,
        description=(
            f"🎫 **Ticket aberto** por {user.mention}\n"
            f"Canal: {ticket_channel.mention}"
        ),
    )


async def handle_close_ticket_request(interaction: discord.Interaction):
    channel = interaction.channel

    if not isinstance(channel, discord.TextChannel) or \
            not channel.name.startswith("ticket-"):
        await interaction.response.send_message(
            "❌ Este botão só funciona dentro de um ticket.",
            ephemeral=True
        )
        return

    await interaction.response.send_message(
        "⚠️ Tem certeza que deseja **fechar** este ticket?\n"
        "O canal será deletado.",
        view=ConfirmCloseView(),
        ephemeral=True
    )


async def handle_close_ticket_confirmed(interaction: discord.Interaction):
    channel = interaction.channel
    guild = interaction.guild
    closer = interaction.user

    owner_id = next(
        (uid for uid, cid in active_tickets.items() if cid == channel.id),
        None
    )

    await interaction.response.edit_message(
        content="🔒 Fechando o ticket...",
        view=None
    )

    embed = discord.Embed(
        title="🔒 Ticket Encerrado",
        description=(
            f"Fechado por {closer.mention}.\n"
            "O canal será deletado em instantes."
        ),
        color=EMBED_COLOR
    )
    embed.set_footer(text="Cards of Doons | Suporte")

    try:
        await channel.send(embed=embed)
    except (discord.Forbidden, discord.HTTPException):
        pass

    if owner_id and owner_id in active_tickets:
        del active_tickets[owner_id]

    ai_disabled_tickets.discard(channel.id)

    logger.info(
        f"Ticket #{channel.name} fechado por {closer} (ID: {closer.id})."
    )

    await _send_log(
        guild=guild,
        bot=interaction.client,
        description=(
            f"🔒 **Ticket fechado** por {closer.mention}\n"
            f"Canal: `{channel.name}`"
        ),
    )

    await asyncio.sleep(3)

    try:
        await channel.delete(reason=f"Ticket fechado por {closer}")
    except (discord.Forbidden, discord.HTTPException) as e:
        logger.error(f"Erro ao deletar #{channel.name}: {e}")


async def handle_call_staff(interaction: discord.Interaction):
    channel = interaction.channel
    guild = interaction.guild
    user = interaction.user

    if not isinstance(channel, discord.TextChannel) or \
            not channel.name.startswith("ticket-"):
        await interaction.response.send_message(
            "❌ Este botão só funciona dentro de um ticket.",
            ephemeral=True
        )
        return

    ai_disabled_tickets.add(channel.id)

    staff_mention = next(
        (
            role.mention for role in guild.roles
            if (role.permissions.manage_guild or role.permissions.administrator)
            and not role.is_bot_managed()
            and not role.is_integration()
        ),
        ""
    )

    embed = discord.Embed(
        title="🛡️ Atendimento Humano Solicitado",
        description=(
            f"{user.mention} solicitou atendimento da equipe.\n\n"
            "🤖 A IA foi **desativada** neste ticket.\n"
            "A equipe irá atender em breve."
        ),
        color=EMBED_COLOR
    )
    embed.set_footer(text="Cards of Doons | Suporte")

    await interaction.response.send_message(
        content=f"{staff_mention} — Atendimento solicitado!" if staff_mention else None,
        embed=embed,
        view=ReactivateAIView()
    )

    logger.info(
        f"Staff chamado em #{channel.name} por {user} (ID: {user.id})."
    )

    await _send_log(
        guild=guild,
        bot=interaction.client,
        description=(
            f"🛡️ **Staff chamado** por {user.mention}\n"
            f"Canal: {channel.mention}"
        ),
    )


async def _send_log(guild: discord.Guild, bot: commands.Bot, description: str):
    if not config.LOG_CHANNEL_ID:
        return
    log_channel = bot.get_channel(config.LOG_CHANNEL_ID)
    if not log_channel:
        return
    try:
        await log_channel.send(
            embed=discord.Embed(
                description=description,
                color=EMBED_COLOR
            ).set_footer(text="Cards of Doons | Log")
        )
    except (discord.Forbidden, discord.HTTPException):
        pass


# ─────────────────────────────────────────
# Cog
# ─────────────────────────────────────────

class Tickets(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.add_view(SetupTicketView())
        self.bot.add_view(TicketActionsView())
        self.bot.add_view(ConfirmCloseView())
        self.bot.add_view(ReactivateAIView())

    @app_commands.command(
        name="setup_ticket",
        description="[STAFF] Envia o painel de tickets neste canal."
    )
    async def setup_ticket(self, interaction: discord.Interaction):
        if not is_staff_interaction(interaction):
            await interaction.response.send_message(
                "❌ Você não tem permissão para usar este comando.",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        embed = discord.Embed(
            title="🎫 SUPORTE — CARDS OF DOONS",
            description=(
                "Precisa de ajuda? Abra um ticket e explique seu problema.\n\n"
                "🤖 O atendimento automático poderá ajudar com dúvidas comuns.\n"
                "🛡️ Caso necessário, a equipe poderá assumir o atendimento.\n\n"
                "Clique no botão abaixo para abrir seu ticket."
            ),
            color=EMBED_COLOR,
        )

        if interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)

        embed.set_footer(
            text="Cards of Doons | Suporte • Um ticket por usuário"
        )

        await interaction.channel.send(embed=embed, view=SetupTicketView())
        await interaction.followup.send(
            "✅ Painel de tickets enviado.",
            ephemeral=True
        )

        logger.info(
            f"{interaction.user} usou /setup_ticket em #{interaction.channel.name}."
        )


async 
