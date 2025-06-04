# cogs/settings.py

import discord
from discord.ext import commands
from discord import app_commands

from database.config_store import get_config, set_config, get_all_config


class Settings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="show_settings", description="(ADMIN ONLY) Show all current bot settings.")
    @app_commands.checks.has_permissions(administrator=True)
    async def show_settings(self, interaction: discord.Interaction):
        config = get_all_config()
        guild = interaction.guild

        friendly_names = {
            "counting_channel_id": "Counting Channel",
            "counting_paused": "Counting Game",
            "welcome_channel_id": "Welcome Channel",
            "welcome_enabled": "Welcome Messages",
            "voice_entry_channel_id": "Join-to-Create Channel",
            "reddit_channel_id": "Reddit Mirror Channel",
            "reddit_enabled": "Reddit Mirror",
            "reddit_min_upvotes": "Reddit Min Upvotes",
            "dune_news_channel_id": "Dune News Channel"
        }

        embed = discord.Embed(
            title="📑 Server Bot Settings",
            color=discord.Color.blurple()
        )

        for key, label in friendly_names.items():
            value = config.get(key)

            if isinstance(value, int) and "channel_id" in key:
                channel = guild.get_channel(value)
                display = channel.mention if channel else f"`#{value}` (not found)"
            elif isinstance(value, bool):
                if key == "counting_paused":
                    display = "❌ Disabled" if value else "✅ Enabled"
                else:
                    display = "✅ Enabled" if value else "❌ Disabled"
            else:
                display = str(value) if value is not None else "*Not set*"

            embed.add_field(name=label, value=display, inline=False)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="toggle_setting", description="(ADMIN ONLY) Toggle a boolean setting (true/false).")
    @app_commands.describe(key="The config key to toggle (must be a boolean)")
    @app_commands.checks.has_permissions(administrator=True)
    async def toggle_setting(self, interaction: discord.Interaction, key: str):
        value = get_config(key)
        if not isinstance(value, bool):
            await interaction.response.send_message(f"❌ `{key}` is not a toggleable boolean.", ephemeral=True)
            return
        new_value = not value
        set_config(key, new_value)
        await interaction.response.send_message(f"✅ `{key}` is now set to `{new_value}`.", ephemeral=True)

    @app_commands.command(name="set_counting_channel", description="(ADMIN ONLY) Set this channel as the counting channel.")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_counting_channel(self, interaction: discord.Interaction):
        set_config("counting_channel_id", interaction.channel.id)
        await interaction.response.send_message(
            f"🔢 Counting channel set to {interaction.channel.mention}.", ephemeral=True
        )

    @app_commands.command(name="set_config", description="(ADMIN ONLY) Set a config key manually.")
    @app_commands.describe(key="The config key to set", value="The value to store")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_config_command(self, interaction: discord.Interaction, key: str, value: str):
        try:
            parsed_value = eval(value, {"__builtins__": {}}, {})
        except Exception:
            parsed_value = value
        set_config(key, parsed_value)
        await interaction.response.send_message(
            f"🛠️ `{key}` updated to `{parsed_value}`.", ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(Settings(bot))
