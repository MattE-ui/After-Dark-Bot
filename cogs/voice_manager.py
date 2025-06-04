# cogs/voice_manager.py

import discord
from discord.ext import commands, tasks
from discord import app_commands
from database.config_store import get_config, set_config
import asyncio
import time

CHANNEL_TIMEOUT_SECONDS = 5  # seconds before deleting empty temp VC


class VoiceManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.temp_channels = {}  # {channel_id: empty_timestamp}
        self.cleanup_task.start()

    def cog_unload(self):
        self.cleanup_task.cancel()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        entry_channel_id = get_config("voice_entry_channel_id")
        if not entry_channel_id:
            return

        # ─── TEMP VC CREATION ─────────────────────────────
        if after.channel and after.channel.id == entry_channel_id:
            category = after.channel.category
            channel_name = f"{member.display_name}'s Channel"

            existing_channel = discord.utils.get(category.voice_channels, name=channel_name)
            if existing_channel:
                await member.move_to(existing_channel)
                return

            new_channel = await category.create_voice_channel(
                name=channel_name,
                overwrites={
                    member.guild.default_role: discord.PermissionOverwrite(connect=True, view_channel=True),
                    member: discord.PermissionOverwrite(manage_channels=True, connect=True, view_channel=True)
                }
            )
            await member.move_to(new_channel)

        # ─── TEMP VC EMPTY TRACKING ───────────────────────
        if before.channel and before.channel.name.endswith("'s Channel"):
            if len(before.channel.members) == 0:
                self.temp_channels[before.channel.id] = time.time()
            else:
                self.temp_channels.pop(before.channel.id, None)

        if after.channel and after.channel.name.endswith("'s Channel"):
            self.temp_channels.pop(after.channel.id, None)

    @tasks.loop(seconds=5)
    async def cleanup_task(self):
        now = time.time()
        to_delete = []
        for channel_id, emptied_at in self.temp_channels.items():
            if now - emptied_at >= CHANNEL_TIMEOUT_SECONDS:
                channel = self.bot.get_channel(channel_id)
                if channel and isinstance(channel, discord.VoiceChannel) and len(channel.members) == 0:
                    try:
                        await channel.delete(reason="Temporary VC expired")
                        to_delete.append(channel_id)
                    except Exception as e:
                        print(f"[VoiceManager] Failed to delete channel {channel_id}: {e}")
                        to_delete.append(channel_id)
        for cid in to_delete:
            self.temp_channels.pop(cid, None)

    @cleanup_task.before_loop
    async def before_cleanup(self):
        await self.bot.wait_until_ready()

    # ───── SLASH COMMANDS ────────────────────────────────

    @app_commands.command(name="set_tempvc_trigger", description="(ADMIN ONLY) Set this voice channel as the Join-to-Create entry.")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_entry_channel(self, interaction: discord.Interaction):
        if isinstance(interaction.channel, discord.VoiceChannel):
            set_config("voice_entry_channel_id", interaction.channel.id)
            await interaction.response.send_message("✅ Join-to-Create voice channel set.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ This must be used inside a voice channel.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(VoiceManager(bot))
