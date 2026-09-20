import logging

import discord
from discord import app_commands
from discord.ext import commands

from services.groq_service import groq_service
from utils.permissions import is_staff_interaction

logger = logging.getLogger("Commands")

EMBED_COLOR = discord.Color(0xe03f3f)


class Commands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="help",
        description="Mostra todos os comandos disponíveis e como utilizá-los."
    )
    async def help_command(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📋 Cards of Doons | BOT — Comandos",
            description=(
                "Confira abaixo todos os comandos disponíveis "
                "e quem pode utilizá-los."
            ),
            color=EMBED_COLOR,
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
                "Envia o painel de suporte com botão de abertura de tickets no canal atual.\n"
                "**Quem pode usar:** Apenas Staff / Administradores."
            ),
            inline=False
        )

        embed.add_field(
            name="📣 `/painel_suporte`",
            value=(
                "Gera um painel de suporte com botão para abrir canal de suporte privado.\n"
                "**Quem pode usar:** Apenas Staff / Administradores."
            ),
            inline=False
        )

        embed.add_field(
            name="🤖 `/ai <pergunta>`",
            value=(
                "Testa a IA de suporte com uma pergunta direta.\n"
                "**Quem pode usar:** Apenas Staff / Administradores."
            ),
            inline=False
        )

        embed.add_field(
            name="🔄 `/sync`",
            value=(
                "Força a sincronização dos slash commands.\n"
                "**Quem pode usar:** Apenas Administradores."
            ),
            inline=False
        )

        embed.add_field(
            name="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            value=(
                "🤖 **IA de Suporte**\n"
                "Dentro dos tickets, a IA responde automaticamente.\n"
                "Clique em **🛡️ Chamar Staff** para solicitar atendimento humano."
            ),
            inline=False
        )

        if interaction.guild and interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)

        embed.set_footer(text="Cards of Doons | BOT • Use /help a qualquer momento")

        await interaction.response.send_message(embed=embed, ephemeral=True)
        logger.info(f"{interaction.user} (ID: {interaction.user.id}) usou /help.")

    @app_commands.command(
        name="ai",
        description="[STAFF] Testa a IA de suporte com uma pergunta."
    )
    @app_commands.describe(
        pergunta="A pergunta que você quer enviar para a IA de suporte."
    )
    async def ai_test(self, interaction: discord.Interaction, pergunta: str):
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

        result = (
            f"**Pergunta:** {pergunta}\n\n"
            f"**Resposta da IA:**\n{response}"
        )

        if len(result) <= 2000:
            await interaction.followup.send(result, ephemeral=True)
        else:
            await interaction.followup.send(
                f"**Pergunta:** {pergunta}\n\n**Resposta da IA:**",
                ephemeral=True
            )
            chunks = [response[i:i + 1900] for i in range(0, len(response), 1900)]
            for chunk in chunks:
                await interaction.followup.send(chunk, ephemeral=True)

        logger.info(
            f"{interaction.user} (ID: {interaction.user.id}) "
            f"testou a IA com: {pergunta[:80]}"
        )

    @app_commands.command(
        name="sync",
        description="[ADMIN] Força a sincronização dos slash commands com o Discord."
    )
    async def sync_commands(self, interaction: discord.Interaction):
        """Sincroniza os slash commands manualmente. Apenas administradores."""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ Apenas administradores podem usar este comando.",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        try:
            # Sincroniza globalmente
            synced = await self.bot.tree.sync()

            cmd_list = "\n".join(f"• `/{c.name}`" for c in synced)

            await interaction.followup.send(
                f"✅ **{len(synced)} comando(s) sincronizado(s):**\n{cmd_list}",
                ephemeral=True
            )

            logger.info(
                f"{interaction.user} forçou sync. "
                f"{len(synced)} comandos sincronizados: "
                f"{[c.name for c in synced]}"
            )

        except discord.HTTPException as e:
            await interaction.followup.send(
                f"❌ Erro ao sincronizar: `{e}`",
                ephemeral=True
            )
            logger.error(f"Erro no /sync: {e}", exc_info=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Commands(bot))
