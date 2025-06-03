
import discord
from discord.ext import commands
from discord import app_commands
import os
import json
from dotenv import load_dotenv

load_dotenv()

CONFIG_PATH = "config.json"

def _load_config() -> dict:
    defaults = {
        "welcome_enabled": False,
        "reddit_enabled": True,
        "reddit_channel_id": None
    }
    if not os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "w") as f:
            json.dump(defaults, f, indent=4)
        return defaults

    with open(CONFIG_PATH, "r") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            data = defaults

    for key, val in defaults.items():
        if key not in data:
            data[key] = val

    return data

def _save_config(cfg: dict):
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=4)

class Settings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._config = _load_config()

    def is_admin(self, interaction: discord.Interaction) -> bool:
        return interaction.user.guild_permissions.administrator

    @app_commands.command(name="toggle_welcome", description="Enable or disable Welcome messages (admin only).")
    async def toggle_welcome(self, interaction: discord.Interaction):
        if not self.is_admin(interaction):
            await interaction.response.send_message("❌ You must be a server admin to use this.", ephemeral=True)
            return

        self._config["welcome_enabled"] = not self._config.get("welcome_enabled", False)
        _save_config(self._config)

        state = "enabled" if self._config["welcome_enabled"] else "disabled"
        await interaction.response.send_message(f"✅ Welcome messages are now **{state}**.")

    @app_commands.command(name="toggle_reddit", description="Enable or disable automatic Reddit mirroring (admin only).")
    async def toggle_reddit(self, interaction: discord.Interaction):
        if not self.is_admin(interaction):
            await interaction.response.send_message("❌ You must be a server admin to use this.", ephemeral=True)
            return

        self._config["reddit_enabled"] = not self._config.get("reddit_enabled", True)
        _save_config(self._config)

        state = "enabled" if self._config["reddit_enabled"] else "disabled"
        await interaction.response.send_message(f"✅ Automatic Reddit mirroring is now **{state}**.")

    @app_commands.command(name="set_reddit_channel", description="Set the channel for Reddit mirroring (admin only).")
    @app_commands.describe(channel="The text channel where r/duneawakening will be mirrored")
    async def set_reddit_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not self.is_admin(interaction):
            await interaction.response.send_message("❌ You must be a server admin to use this.", ephemeral=True)
            return

        self._config["reddit_channel_id"] = channel.id
        _save_config(self._config)

        await interaction.response.send_message(f"✅ Reddit mirroring destination set to {channel.mention}.")

    @app_commands.command(name="show_settings", description="Show current bot configuration (admin only).")
    async def show_settings(self, interaction: discord.Interaction):
        if not self.is_admin(interaction):
            await interaction.response.send_message("❌ You must be a server admin to use this.", ephemeral=True)
            return

        parts = []
        parts.append(f"• Welcome Enabled: `{self._config.get('welcome_enabled')}`")
        parts.append(f"• Reddit Mirroring Enabled: `{self._config.get('reddit_enabled')}`")
        reddit_chan = self._config.get("reddit_channel_id")
        if reddit_chan:
            parts.append(f"• Reddit Channel ID: `{reddit_chan}`")
        else:
            parts.append("• Reddit Channel ID: `Not Set`")

        embed = discord.Embed(
            title="Bot Settings",
            description="\n".join(parts),
            color=discord.Color.blurple()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Settings(bot))
