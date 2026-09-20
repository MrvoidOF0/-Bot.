import discord
from discord import Interaction


def is_staff(member: discord.Member) -> bool:
    """
    Retorna True se o membro possui permissão de administrador
    ou a permissão de gerenciar o servidor (staff).
    """
    if member.guild_permissions.administrator:
        return True
    if member.guild_permissions.manage_guild:
        return True
    if member.guild_permissions.manage_channels:
        return True
    return False


def is_staff_interaction(interaction: Interaction) -> bool:
    """Verifica se o usuário da interação é staff."""
    if not isinstance(interaction.user, discord.Member):
        return False
    return is_staff(interaction.user)
