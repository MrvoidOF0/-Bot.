import logging

import discord
from discord import app_commands
from discord.ext import commands

from utils.config import config
from utils.permissions import is_staff_interaction

logger = logging.getLogger("PainelSuporte")

EMBED_COLOR = discord.Color(0xe03f3f)


# ─────────────────────────────────────────
# Estado: canais de suporte abertos
# ─────────────────────────────────────────
# {user_id: channel_id}
active_support_channels: dict[int, int] = {}


# ─────────────────────────────────────────
# View do painel de suporte
# ─────────────────────────────────────────

class PainelSuporteView(discord.ui.View):
    """View persistente com o botão de abrir canal de suporte."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🎫 Abrir Canal de Suporte",
        style=discord.ButtonStyle.primary,
        custom_id="painel_abrir_suporte_button"
    )
    async def abrir_suporte(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await handle_abrir_suporte(interaction)


class SupportChannelActionsView(discord.ui.View):
    """View com botões dentro do canal de suporte."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🔒 Fechar Canal",
        style=discord.ButtonStyle.danger,
        custom_id="suporte_fechar_button"
    )
    async def fechar_canal(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await handle_fechar_suporte_request(interaction)

    @discord.ui.button(
        label="🛡️ Chamar Staff",
        style=discord.ButtonStyle.secondary,
        custom_id="suporte_staff_button"
    )
    async def chamar_staff(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await handle_chamar_staff_suporte(interaction)


class ConfirmFecharSuporteView(discord.ui.View):
    """Confirmação para fechar o canal de suporte."""

    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.button(
        label="✅ Confirmar Fechamento",
        style=discord.ButtonStyle.danger,
        custom_id="suporte_confirmar_fechar_button"
    )
    async def confirmar(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await handle_fechar_suporte_confirmed(interaction)

    @discord.ui.button(
        label="❌ Cancelar",
        style=discord.ButtonStyle.secondary,
        custom_id="suporte_cancelar_fechar_button"
    )
    async def cancelar(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.edit_message(
            content="✅ Fechamento cancelado. O canal permanece aberto.",
            view=None
        )


# ─────────────────────────────────────────
# Handlers
# ─────────────────────────────────────────

async def handle_abrir_suporte(interaction: discord.Interaction):
    """Cria um canal de suporte privado para o usuário."""
    user = interaction.user
    guild = interaction.guild

    # Verifica se já possui canal de suporte aberto
    if user.id in active_support_channels:
        existing_channel = guild.get_channel(active_support_channels[user.id])
        if existing_channel:
            await interaction.response.send_message(
                f"❌ Você já possui um canal de suporte aberto: {existing_channel.mention}\n"
                "Utilize o canal existente para continuar.",
                ephemeral=True
            )
            return
        else:
            del active_support_channels[user.id]

    # Busca a categoria dos tickets
    category = guild.get_channel(config.TICKET_CATEGORY_ID)
    if category is None or not isinstance(category, discord.CategoryChannel):
        await interaction.response.send_message(
            "❌ A categoria de suporte não foi encontrada. Contate um administrador.",
            ephemeral=True
        )
        logger.error(f"Categoria não encontrada (ID: {config.TICKET_CATEGORY_ID}).")
        return

    await interaction.response.defer(ephemeral=True)

    # Permissões do canal
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
            overwrites[role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_messages=True,
                read_message_history=True,
                manage_messages=True
            )

    # Sanitiza o nome
    safe_name = "".join(
        c if c.isalnum() or c in "-_" else "-"
        for c in user.display_name.lower()
    ).strip("-")[:20]

    if not safe_name:
        safe_name = str(user.id)[:10]

    channel_name = f"suporte-{safe_name}"

    try:
        support_channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites,
            topic=f"Canal de suporte de {user} (ID: {user.id})"
        )
    except discord.Forbidden:
        await interaction.followup.send(
            "❌ Sem permissão para criar o canal. Contate um administrador.",
            ephemeral=True
        )
        return
    except discord.HTTPException as e:
        await interaction.followup.send(
            f"❌ Erro ao criar o canal de suporte: {e}",
            ephemeral=True
        )
        return

    active_support_channels[user.id] = support_channel.id
    logger.info(f"Canal de suporte criado: #{support_channel.name} para {user} (ID: {user.id}).")

    embed = discord.Embed(
        title="🎫 Canal de Suporte — Cards of Doons",
        description=(
            f"Olá, {user.mention}!\n\n"
            "Descreva sua dúvida ou problema com o máximo de detalhes possível.\n\n"
            "🛡️ Nossa equipe irá atender você em breve.\n\n"
            "⚠️ **Nunca envie senhas, tokens ou informações pessoais.**"
        ),
        color=EMBED_COLOR,
    )
    embed.set_footer(text="Cards of Doons | Suporte")

    await support_channel.send(
        content=user.mention,
        embed=embed,
        view=SupportChannelActionsView()
    )

    await interaction.followup.send(
        f"✅ Seu canal de suporte foi criado: {support_channel.mention}",
        ephemeral=True
    )

    await _send_support_log(
        guild=guild,
        bot=interaction.client,
        description=f"🎫 **Canal de suporte aberto** por {user.mention}\nCanal: {support_channel.mention}",
    )


async def handle_fechar_suporte_request(interaction: discord.Interaction):
    """Pede confirmação antes de fechar o canal de suporte."""
    channel = interaction.channel

    if not isinstance(channel, discord.TextChannel) or not channel.name.startswith("suporte-"):
        await interaction.response.send_message(
            "❌ Este botão só pode ser usado dentro de um canal de suporte.",
            ephemeral=True
        )
        return

    await interaction.response.send_message(
        "⚠️ Tem certeza que deseja **fechar** este canal de suporte?\n"
        "Esta ação encerrará o atendimento e o canal será deletado.",
        view=ConfirmFecharSuporteView(),
        ephemeral=True
    )


async def handle_fechar_suporte_confirmed(interaction: discord.Interaction):
    """Fecha e deleta o canal de suporte."""
    import asyncio

    channel = interaction.channel
    guild = interaction.guild
    closer = interaction.user

    owner_id = None
    for uid, cid in list(active_support_channels.items()):
        if cid == channel.id:
            owner_id = uid
            break

    await interaction.response.edit_message(
        content="🔒 Fechando o canal de suporte...",
        view=None
    )

    embed = discord.Embed(
        title="🔒 Canal de Suporte Encerrado",
        description=(
            f"Este canal foi fechado por {closer.mention}.\n"
            "O canal será deletado em instantes."
        ),
        color=EMBED_COLOR
    )
    embed.set_footer(text="Cards of Doons | Suporte")

    try:
        await channel.send(embed=embed)
    except (discord.Forbidden, discord.HTTPException):
        pass

    if owner_id and owner_id in active_support_channels:
        del active_support_channels[owner_id]

    logger.info(f"Canal de suporte #{channel.name} fechado por {closer} (ID: {closer.id}).")

    await _send_support_log(
        guild=guild,
        bot=interaction.client,
        description=f"🔒 **Canal de suporte fechado** por {closer.mention}\nCanal: `{channel.name}`",
    )

    await asyncio.sleep(3)

    try:
        await channel.delete(reason=f"Canal de suporte fechado por {closer}")
    except discord.Forbidden:
        logger.error(f"Sem permissão para deletar #{channel.name}.")
    except discord.HTTPException as e:
        logger.error(f"Erro ao deletar #{channel.name}: {e}")


async def handle_chamar_staff_suporte(interaction: discord.Interaction):
    """Notifica a staff no canal de suporte."""
    channel = interaction.channel
    guild = interaction.guild
    user = interaction.user

    if not isinstance(channel, discord.TextChannel) or not channel.name.startswith("suporte-"):
        await interaction.response.send_message(
            "❌ Este botão só pode ser usado dentro de um canal de suporte.",
            ephemeral=True
        )
        return

    staff_mention = ""
    for role in guild.roles:
        if role.permissions.manage_guild or role.permissions.administrator:
            if not role.is_bot_managed() and not role.is_integration():
                staff_mention = role.mention
                break

    embed = discord.Embed(
        title="🛡️ Equipe Solicitada",
        description=(
            f"{user.mention} solicitou atendimento de um membro da equipe.\n\n"
            "Um membro da equipe irá atender em breve."
        ),
        color=EMBED_COLOR
    )
    embed.set_footer(text="Cards of Doons | Suporte")

    content = f"{staff_mention} — Atendimento solicitado!" if staff_mention else None

    await interaction.response.send_message(
        content=content,
        embed=embed
    )

    logger.info(f"Staff chamada em #{channel.name} por {user} (ID: {user.id}).")

    await _send_support_log(
        guild=guild,
        bot=interaction.client,
        description=f"🛡️ **Staff chamada** por {user.mention}\nCanal: {channel.mention}",
    )


async def _send_support_log(
    guild: discord.Guild,
    bot: commands.Bot,
    description: str
):
    """Envia log no canal configurado."""
    if not config.LOG_CHANNEL_ID:
        return

    log_channel = bot.get_channel(config.LOG_CHANNEL_ID)
    if log_channel is None:
        return

    embed = discord.Embed(
        description=description,
        color=discord.Color(0xe03f3f)
    )
    embed.set_footer(text="Cards of Doons | Log")

    try:
        await log_channel.send(embed=embed)
    except (discord.Forbidden, discord.HTTPException):
        pass


# ─────────────────────────────────────────
# Cog
# ─────────────────────────────────────────

class PainelSuporte(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.add_view(PainelSuporteView())
        self.bot.add_view(SupportChannelActionsView())
        self.bot.add_view(ConfirmFecharSuporteView())

    @app_commands.command(
        name="painel_suporte",
        description="[STAFF] Gera um painel de suporte com botão para abrir canal."
    )
    async def painel_suporte(self, interaction: discord.Interaction):
        """Envia o painel de suporte com botão. Apenas staff."""
        if not is_staff_interaction(interaction):
            await interaction.response.send_message(
                "❌ Você não tem permissão para usar este comando.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "✅ Painel de suporte enviado.",
            ephemeral=True
        )

        embed = discord.Embed(
            title="🛡️ SUPORTE OFICIAL — CARDS OF DOONS",
            description=(
                "Precisa de ajuda com o jogo, sua conta ou tem alguma dúvida?\n\n"
                "Clique no botão abaixo para abrir um **canal de suporte privado**.\n"
                "Nossa equipe estará disponível para te atender.\n\n"
                "📌 **Antes de abrir um canal:**\n"
                "— Verifique se sua dúvida não está nas informações do servidor.\n"
                "— Descreva seu problema com o máximo de detalhes.\n\n"
                "⚠️ **Nunca compartilhe senhas ou dados pessoais.**"
            ),
            color=EMBED_COLOR,
        )

        if interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)

        embed.set_footer(
            text="Cards of Doons | Suporte • Um canal por usuário"
        )

        await interaction.channel.send(
            embed=embed,
            view=PainelSuporteView()
        )

        logger.info(
            f"{interaction.user} executou /painel_suporte em #{interaction.channel.name}."
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(PainelSuporte(bot))
