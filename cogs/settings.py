
import discord
from discord.ext import commands
from discord import app_commands
import os
import json
from dotenv import load_dotenv

load_dotenv()

CONFIG_PATH = "config.json"

def _load_config() -> dict:
    """
    Load the JSON config file, ensuring defaults exist.
    """
    defaults = {
        "welcome_enabled": False,
        "reddit_enabled": True,
        "reddit_channel_id": None,
        "counting_channel_id": None,
        "counting_paused": False,
        "current_count": 0
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

    # Ensure all keys exist
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

    @app_commands.command(name="toggle_welcome", description="Enable or disable Welcome messages (Admin only).")
    async def toggle_welcome(self, interaction: discord.Interaction):
        if not self.is_admin(interaction):
            await interaction.response.send_message("❌ You must be a server admin to use this.", ephemeral=True)
            return

        self._config["welcome_enabled"] = not self._config.get("welcome_enabled", False)
        _save_config(self._config)
        state = "enabled" if self._config["welcome_enabled"] else "disabled"
        await interaction.response.send_message(f"✅ Welcome messages are now **{state}**.")

    @app_commands.command(name="toggle_reddit", description="Enable or disable Reddit mirroring (Admin only).")
    async def toggle_reddit(self, interaction: discord.Interaction):
        if not self.is_admin(interaction):
            await interaction.response.send_message("❌ You must be a server admin to use this.", ephemeral=True)
            return

        self._config["reddit_enabled"] = not self._config.get("reddit_enabled", True)
        _save_config(self._config)
        state = "enabled" if self._config["reddit_enabled"] else "disabled"
        await interaction.response.send_message(f"✅ Reddit mirroring is now **{state}**.")

    @app_commands.command(name="set_reddit_channel", description="Set the channel for Reddit mirroring (Admin only).")
    @app_commands.describe(channel="Text channel where Reddit posts will be mirrored")
    async def set_reddit_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not self.is_admin(interaction):
            await interaction.response.send_message("❌ You must be a server admin to use this.", ephemeral=True)
            return

        self._config["reddit_channel_id"] = channel.id
        _save_config(self._config)
        await interaction.response.send_message(f"✅ Reddit mirroring destination set to {channel.mention}.")

    @app_commands.command(name="set_count_channel", description="Set the channel for the counting game (Admin only).")
    @app_commands.describe(channel="Text channel where counting game will run")
    async def set_count_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not self.is_admin(interaction):
            await interaction.response.send_message("❌ You must be a server admin to use this.", ephemeral=True)
            return

        self._config["counting_channel_id"] = channel.id
        self._config["current_count"] = 0
        self._config["counting_paused"] = False
        _save_config(self._config)
        await interaction.response.send_message(f"✅ Counting game channel set to {channel.mention}. Count reset to 0.")

    @app_commands.command(name="toggle_counting", description="Pause or resume the counting game (Admin only).")
    async def toggle_counting(self, interaction: discord.Interaction):
        if not self.is_admin(interaction):
            await interaction.response.send_message("❌ You must be a server admin to use this.", ephemeral=True)
            return

        self._config["counting_paused"] = not self._config.get("counting_paused", False)
        _save_config(self._config)
        state = "paused" if self._config["counting_paused"] else "resumed"
        await interaction.response.send_message(f"✅ Counting game has been **{state}**. Current count remains {self._config['current_count']}.")

    @app_commands.command(name="set_count", description="Set the current count to a specific number (Admin only).")
    @app_commands.describe(number="The number to set as current count")
    async def set_count(self, interaction: discord.Interaction, number: int):
        if not self.is_admin(interaction):
            await interaction.response.send_message("❌ You must be a server admin to use this.", ephemeral=True)
            return

        if number < 0:
            await interaction.response.send_message("❌ Please provide a non-negative integer.", ephemeral=True)
            return

        self._config["current_count"] = number
        _save_config(self._config)
        await interaction.response.send_message(f"✅ Current count has been set to **{number}**.")

    @app_commands.command(name="skip_to", description="Skip counting to a specific number (Admin only).")
    @app_commands.describe(number="Number to skip to (must be ≥ current_count+1)")
    async def skip_count_to(self, interaction: discord.Interaction, number: int):
        if not self.is_admin(interaction):
            await interaction.response.send_message("❌ You must be a server admin to use this.", ephemeral=True)
            return

        current = self._config.get("current_count", 0)
        if number < current + 1:
            await interaction.response.send_message(f"❌ You can only skip to at least {current + 1}. (Current count = {current})", ephemeral=True)
            return

        self._config["current_count"] = number
        _save_config(self._config)
        await interaction.response.send_message(f"✅ Skipped counting to **{number}**. Next expected is {number + 1}.")

    @app_commands.command(name="admin_view_stats", description="View counting stats (Admin only).")
    async def admin_view_stats(self, interaction: discord.Interaction):
        if not self.is_admin(interaction):
            await interaction.response.send_message("❌ You must be a server admin to use this.", ephemeral=True)
            return

        stats = {}
        try:
            with open("counting_stats.json", "r") as f:
                stats = json.load(f)
        except FileNotFoundError:
            stats = {
                "high_count": 0,
                "user_highs": {},
                "total_counts": {},
                "fail_counts": {}
            }

        high_count = stats.get("high_count", 0)
        user_highs = stats.get("user_highs", {})
        total_counts = stats.get("total_counts", {})
        fail_counts = stats.get("fail_counts", {})

        embed = discord.Embed(title="Counting Game Stats", color=discord.Color.green())
        embed.add_field(name="🔢 Global High Count", value=str(high_count), inline=False)

        if user_highs:
            sorted_highs = sorted(user_highs.items(), key=lambda x: x[1], reverse=True)[:5]
            desc = "\n".join(f"<@{uid}>: {val}" for uid, val in sorted_highs)
            embed.add_field(name="🏆 Top Personal Highs", value=desc, inline=False)

        if total_counts:
            sorted_totals = sorted(total_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            desc2 = "\n".join(f"<@{uid}>: {val}" for uid, val in sorted_totals)
            embed.add_field(name="🔁 Top Contributors", value=desc2, inline=False)

        if fail_counts:
            sorted_fails = sorted(fail_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            desc3 = "\n".join(f"<@{uid}>: {val}" for uid, val in sorted_fails)
            embed.add_field(name="❌ Top Failures", value=desc3, inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="show_settings", description="Show current bot configuration (Admin only).")
    async def show_settings(self, interaction: discord.Interaction):
        if not self.is_admin(interaction):
            await interaction.response.send_message("❌ You must be a server admin to use this.", ephemeral=True)
            return

        parts = [
            f"• Welcome Enabled: `{self._config.get('welcome_enabled')}`",
            f"• Reddit Mirroring Enabled: `{self._config.get('reddit_enabled')}`",
        ]
        reddit_chan = self._config.get("reddit_channel_id")
        if reddit_chan:
            parts.append(f"• Reddit Channel ID: `{reddit_chan}`")
        else:
            parts.append("• Reddit Channel ID: `Not Set`")

        count_chan = self._config.get("counting_channel_id")
        if count_chan:
            parts.append(f"• Counting Channel ID: `{count_chan}`")
        else:
            parts.append("• Counting Channel ID: `Not Set`")

        parts.append(f"• Counting Paused: `{self._config.get('counting_paused')}`")
        parts.append(f"• Current Count: `{self._config.get('current_count')}`")

        embed = discord.Embed(
            title="Bot Settings",
            description="\n".join(parts),
            color=discord.Color.blurple()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Settings(bot))
