
import discord
from discord.ext import commands
from discord import app_commands
from cogs.config_store import get_setting, set_setting

class Settings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="set_counting_channel", description="Set the counting channel.")
    async def set_counting_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        set_setting("counting_channel_id", channel.id)
        await interaction.response.send_message(f"✅ Counting channel set to {channel.mention}", ephemeral=True)

    @app_commands.command(name="set_reddit_channel", description="Set the channel for Reddit posts.")
    async def set_reddit_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        set_setting("reddit_channel_id", channel.id)
        await interaction.response.send_message(f"📨 Reddit posts will now go to {channel.mention}", ephemeral=True)

    @app_commands.command(name="toggle_reddit", description="Enable or disable Reddit mirroring.")
    async def toggle_reddit(self, interaction: discord.Interaction):
        current = bool(int(get_setting("reddit_enabled", 0)))
        set_setting("reddit_enabled", int(not current))
        status = "enabled" if not current else "disabled"
        await interaction.response.send_message(f"🔁 Reddit mirroring is now **{status}**", ephemeral=True)

    @app_commands.command(name="toggle_chat_flexibility", description="Toggle if messages between counts are allowed.")
    async def toggle_chat_flexibility(self, interaction: discord.Interaction):
        current = bool(int(get_setting("allow_chat_between_counts", 0)))
        set_setting("allow_chat_between_counts", int(not current))
        status = "allowed" if not current else "disallowed"
        await interaction.response.send_message(f"💬 Non-number messages are now **{status}** between counts.", ephemeral=True)

    @app_commands.command(name="pause_counting", description="Pause the counting game.")
    async def pause_counting(self, interaction: discord.Interaction):
        set_setting("counting_paused", 1)
        await interaction.response.send_message("⏸️ Counting has been paused.", ephemeral=True)

    @app_commands.command(name="resume_counting", description="Resume the counting game.")
    async def resume_counting(self, interaction: discord.Interaction):
        set_setting("counting_paused", 0)
        await interaction.response.send_message("▶️ Counting has been resumed.", ephemeral=True)

    @app_commands.command(name="show_settings", description="Show current bot configuration.")
    async def show_settings(self, interaction: discord.Interaction):
        counting_channel = get_setting("counting_channel_id", "Not set")
        reddit_channel = get_setting("reddit_channel_id", "Not set")
        count = get_setting("current_count", "0")
        chat_allowed = bool(int(get_setting("allow_chat_between_counts", 0)))
        reddit_enabled = bool(int(get_setting("reddit_enabled", 0)))
        paused = bool(int(get_setting("counting_paused", 0)))

        message = (
            f"🔧 **Current Bot Settings:**"
            f"📊 Current Count: `{count}`"
            f"#️⃣ Counting Channel ID: `{counting_channel}`"
            f"📬 Reddit Channel ID: `{reddit_channel}`"
            f"💬 Allow Chat Between Counts: `{chat_allowed}`"
            f"🔁 Reddit Mirroring Enabled: `{reddit_enabled}`"
            f"⏸️ Counting Paused: `{paused}`"
        )
        await interaction.response.send_message(message, ephemeral=False)

async def setup(bot):
    await bot.add_cog(Settings(bot))
