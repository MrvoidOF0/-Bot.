import logging

import discord
from discord import app_commands
from discord.ext import commands

from utils.config import config
from utils.permissions import is_staff_interaction

logger = logging.getLogger("Welcome")

EMBED_COLOR = discord.Color(0xe03f3f)


def build_welcome_embed(member: discord.Member) -> discord.Embed:
    """Constrói o embed de boas-vindas."""

    embed = discord.Embed(
        title="🎴 Bem-vindo ao Cards of Doons!",
        description=(
            f"Olá, {member.mention}! Seja bem-vindo ao servidor oficial do **Cards of Doons**.\n\n"
            "Você acaba de entrar no servidor oficial do Cards of Doons.\n"
            "Aqui você poderá acompanhar **atualizações**, **novidades**, **devlogs**, "
            "**eventos** e **anúncios** do jogo, além de conversar com a comunidade.\n\n"
            "Confira as informações do servidor e prepare-se para jogar. 🃏"
        ),
        color=EMBED_COLOR,
    )

    # Thumbnail = foto de perfil do membro
    embed.set_thumbnail(url=member.display_avatar.url)

    # Author com ícone do servidor
    if member.guild.icon:
        embed.set_author(
            name="Cards of Doons",
            icon_url=member.guild.icon.url
        )
    else:
        embed.set_author(name="Cards of Doons")

    embed.add_field(
        name="📢 Anúncios & Atualizações",
        value="Fique por dentro de tudo que acontece no jogo.",
        inline=True
    )
    embed.add_field(
        name="🎮 Comunidade",
        value="Converse com outros jogadores e a equipe.",
        inline=True
    )
    embed.add_field(
        name="🎫 Suporte",
        value="Precisa de ajuda? Abra um ticket com nossa equipe.",
        inline=True
    )

    embed.set_footer(
        text=f"Membro #{member.guild.member_count} • Cards of Doons",
        icon_url=member.guild.icon.url if member.guild.icon else None
    )

    return embed


class Welcome(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Dispara automaticamente quando um novo membro entra no servidor."""
        channel = self.bot.get_channel(config.WELCOME_CHANNEL_ID)

        if channel is None:
            logger.warning(
                f"Canal de boas-vindas não encontrado (ID: {config.WELCOME_CHANNEL_ID}). "
                "Verifique a variável WELCOME_CHANNEL_ID."
            )
            return

        if not isinstance(channel, discord.TextChannel):
            logger.warning(
                f"O canal de boas-vindas (ID: {config.WELCOME_CHANNEL_ID}) "
                "não é um canal de texto válido."
            )
            return

        try:
            embed = build_welcome_embed(member)
            await channel.send(embed=embed)
            logger.info(
                f"Boas-vindas enviadas para {member} (ID: {member.id}) "
                f"no canal #{channel.name}."
            )
        except discord.Forbidden:
            logger.error(
                f"Sem permissão para enviar mensagem no canal de boas-vindas "
                f"(ID: {config.WELCOME_CHANNEL_ID})."
            )
        except discord.HTTPException as e:
            logger.error(f"Erro HTTP ao enviar boas-vindas: {e}")

    @app_commands.command(
        name="testwelcome",
        description="[STAFF] Envia uma simulação da mensagem de boas-vindas."
    )
    async def testwelcome(self, interaction: discord.Interaction):
        """Simula a mensagem de boas-vindas no canal configurado. Apenas staff."""
        if not is_staff_interaction(interaction):
            await interaction.response.send_message(
                "❌ Você não tem permissão para usar este comando.",
                ephemeral=True
            )
            return

        channel = self.bot.get_channel(config.WELCOME_CHANNEL_ID)

        if channel is None:
            await interaction.response.send_message(
                f"❌ Canal de boas-vindas não encontrado.\n"
                f"ID configurado: `{config.WELCOME_CHANNEL_ID}`\n"
                "Verifique a variável de ambiente `WELCOME_CHANNEL_ID`.",
                ephemeral=True
            )
            return

        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                "❌ O canal de boas-vindas não é um canal de texto válido.",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        try:
            embed = build_welcome_embed(interaction.user)
            await channel.send(embed=embed)
            await interaction.followup.send(
                f"✅ Mensagem de boas-vindas enviada em {channel.mention}.",
                ephemeral=True
            )
            logger.info(
                f"{interaction.user} (ID: {interaction.user.id}) "
                "executou /testwelcome com sucesso."
            )
        except discord.Forbidden:
            await interaction.followup.send(
                f"❌ Sem permissão para enviar mensagem em {channel.mention}.",
                ephemeral=True
            )
        except discord.HTTPException as e:
            await interaction.followup.send(
                f"❌ Erro ao enviar a mensagem: {e}",
                ephemeral=True
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(Welcome(bot))
