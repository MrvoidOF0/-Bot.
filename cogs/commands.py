import logging

import discord
from discord import app_commands
from discord.ext import commands

from services.groq_service import groq_service
from utils.permissions import is_staff_interaction

logger = logging.getLogger("Commands")


class Commands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="help",
        description="Mostra todos os comandos disponíveis e como utilizá-los."
    )
    async def help_command(self, interaction: discord.Interaction):
        """Exibe o painel de ajuda com todos os comandos."""

        embed = discord.Embed(
            title="📋 Cards of Doons | BOT — Comandos",
            description="Confira abaixo todos os comandos disponíveis e quem pode utilizá-los.",
            color=discord.Color.from_rgb(138, 43, 226),
        )

        embed.add_field(
            name="📋 `/help`",
            value=(
                "Exibe este painel de ajuda.\n"
                "**Quem pode usar:** Todos os membros."
            ),
            inline=False
        )

        embed.add_field(
            name="👋 `/testwelcome`",
            value=(
                "Envia uma simulação da mensagem de boas-vindas no canal configurado.\n"
                "**Quem pode usar:** Apenas Staff / Administradores."
            ),
            inline=False
        )

        embed.add_field(
            name="🎫 `/setup_ticket`",
            value=(
                "Envia o painel de suporte com o botão de abertura de tickets.\n"
                "Deve ser usado no canal de suporte do servidor.\n"
                "**Quem pode usar:** Apenas Staff / Administradores."
            ),
            inline=False
        )

        embed.add_field(
            name="🤖 `/ai <pergunta>`",
            value=(
                "Testa a IA de suporte diretamente.\n"
                "Útil para verificar se a IA está funcionando corretamente.\n"
                "**Quem pode usar:** Apenas Staff / Administradores."
            ),
            inline=False
        )

        embed.add_field(
            name="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            value=(
                "🤖 **IA de Suporte**\n"
                "Dentro dos tickets, a IA responde automaticamente às mensagens dos usuários.\n"
                "Clique em 🛡️ **Chamar Staff** para solicitar atendimento humano."
            ),
            inline=False
        )

        if interaction.guild and interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)

        embed.set_footer(text="Cards of Doons | BOT • Use /help a qualquer momento")

        await interaction.response.send_message(embed=embed, ephemeral=True)
        logger.info(f"{interaction.user} usou /help.")

    @app_commands.command(
        name="ai",
        description="[STAFF] Testa a IA de suporte com uma pergunta."
    )
    @app_commands.describe(pergunta="A pergunta que você quer enviar para a IA.")
    async def ai_test(self, interaction: discord.Interaction, pergunta: str):
        """Testa a IA de suporte. Apenas staff."""
        if not is_staff_interaction(interaction):
            await interaction.response.send_message(
                "❌ Você não tem permissão para usar este comando.",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        response, _ = await groq_service.chat(
            user_message=pergunta,
            history=[]
        )

        embed = discord.Embed(
            title="🤖 Teste de IA — Cards of Doons",
            color=discord.Color.from_rgb(138, 43, 226),
        )
        embed.add_field(name="📝 Pergunta", value=pergunta[:1024], inline=False)
        embed.add_field(name="🤖 Resposta", value=response[:1024], inline=False)
        embed.set_footer(text=f"Modelo: {groq_service.model}")

        await interaction.followup.send(embed=embed, ephemeral=True)
        logger.info(f"{interaction.user} testou a IA com: {pergunta[:50]}")


async def setup(bot: commands.Bot):
    await bot.add_cog(Commands(bot))
