# cogs/welcome.py

import discord
from discord.ext import commands
from discord import app_commands

from database.config_store import get_config, set_config

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if not get_config("welcome_enabled"):
            return

        channel_id = get_config("welcome_channel_id")
        if not channel_id:
            return

        channel = member.guild.get_channel(int(channel_id))
        if not channel or not isinstance(channel, discord.TextChannel):
            return

        await channel.send(f"👋 Welcome to the server, {member.mention}!")

    @app_commands.command(name="toggle_welcome", description="(ADMIN ONLY) Enable or disable welcome messages.")
    @app_commands.checks.has_permissions(administrator=True)
    async def toggle_welcome(self, interaction: discord.Interaction):
        current = get_config("welcome_enabled") or False
        set_config("welcome_enabled", not current)
        await interaction.response.send_message(f"✅ Welcome messages are now set to `{not current}`.", ephemeral=True)

    @app_commands.command(name="set_welcome_channel", description="(ADMIN ONLY) Set this channel for welcome messages.")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_welcome_channel(self, interaction: discord.Interaction):
        if isinstance(interaction.channel, discord.TextChannel):
            set_config("welcome_channel_id", interaction.channel.id)
            await interaction.response.send_message("📬 Welcome channel set to this channel.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Must be used in a text channel.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Welcome(bot))
