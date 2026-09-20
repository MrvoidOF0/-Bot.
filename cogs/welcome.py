import logging

import discord
from discord import app_commands
from discord.ext import commands

from utils.config import config
from utils.permissions import is_staff_interaction

logger = logging.getLogger("Welcome")


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
        color=discord.Color.from_rgb(138, 43, 226),
    )

    embed.set_thumbnail(url=member.display_avatar.url)

    if member.guild.icon:
        embed.set_author(
            name="Cards of Doons",
            icon_url=member.guild.icon.url
        )

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

    embed.set_image(
        url="https://i.imgur.com/placeholder_banner.png"
    )

    return embed


class Welcome(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Dispara quando um novo membro entra no servidor."""
        channel = self.bot.get_channel(config.WELCOME_CHANNEL_ID)

        if channel is None:
            logger.warning(
                f"Canal de boas-vindas (ID: {config.WELCOME_CHANNEL_ID}) não encontrado. "
                "Verifique a variável WELCOME_CHANNEL_ID."
            )
            return

        try:
            embed = build_welcome_embed(member)
            await channel.send(embed=embed)
            logger.info(f"Boas-vindas enviadas para {member} no canal {channel.name}.")
        except discord.Forbidden:
            logger.error(
                f"Sem permissão para enviar mensagem no canal de boas-vindas (ID: {config.WELCOME_CHANNEL_ID})."
            )
        except discord.HTTPException as e:
            logger.error(f"Erro HTTP ao enviar boas-vindas: {e}")

    @app_commands.command(
        name="testwelcome",
        description="[STAFF] Envia uma simulação da mensagem de boas-vindas."
    )
    async def testwelcome(self, interaction: discord.Interaction):
        """Comando de teste da mensagem de boas-vindas. Apenas staff."""
        if not is_staff_interaction(interaction):
            await interaction.response.send_message(
                "❌ Você não tem permissão para usar este comando.",
                ephemeral=True
            )
            return

        channel = self.bot.get_channel(config.WELCOME_CHANNEL_ID)

        if channel is None:
            await interaction.response.send_message(
                f"❌ Canal de boas-vindas não encontrado (ID: `{config.WELCOME_CHANNEL_ID}`).\n"
                "Verifique a variável de ambiente `WELCOME_CHANNEL_ID`.",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        try:
            embed = build_welcome_embed(interaction.user)
            await channel.send(embed=embed)
            await interaction.followup.send(
                f"✅ Mensagem de boas-vindas enviada para {channel.mention}.",
                ephemeral=True
            )
            logger.info(f"{interaction.user} executou /testwelcome.")
        except discord.Forbidden:
            await interaction.followup.send(
                f"❌ Sem permissão para enviar mensagem em {channel.mention}.",
                ephemeral=True
            )
        except discord.HTTPException as e:
            await interaction.followup.send(
                f"❌ Erro ao enviar mensagem: {e}",
                ephemeral=True
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(Welcome(bot))
