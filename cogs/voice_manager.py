
import discord
from discord.ext import commands, tasks
import asyncio
import time

CREATE_VC_CHANNEL_NAME = "₊ Join to Create"
CHANNEL_TIMEOUT_SECONDS = 5  # delete after 5s of being empty

class VoiceManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.temp_channels = {}  # {channel_id: timestamp_when_emptied}
        self.cleanup_task.start()

    def cog_unload(self):
        self.cleanup_task.cancel()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if after.channel and after.channel.name == CREATE_VC_CHANNEL_NAME:
            category = after.channel.category
            channel_name = f"{member.display_name}'s Channel"

            # Check if user's personal channel already exists
            existing_channel = discord.utils.get(category.voice_channels, name=channel_name)
            if existing_channel:
                await member.move_to(existing_channel)
                return

            # Create a new voice channel
            new_channel = await category.create_voice_channel(
                name=channel_name,
                overwrites={
                    member.guild.default_role: discord.PermissionOverwrite(connect=True, view_channel=True),
                    member: discord.PermissionOverwrite(manage_channels=True, connect=True, view_channel=True)
                }
            )
            await member.move_to(new_channel)

        # Track when a temp VC becomes empty
        if before.channel and before.channel.name.endswith("'s Channel"):
            if len(before.channel.members) == 0:
                self.temp_channels[before.channel.id] = time.time()
            else:
                self.temp_channels.pop(before.channel.id, None)

        # Cancel deletion if someone joins the tracked channel
        if after.channel and after.channel.name.endswith("'s Channel"):
            self.temp_channels.pop(after.channel.id, None)

    @tasks.loop(seconds=30)
    async def cleanup_task(self):
        now = time.time()
        to_delete = []
        for channel_id, empty_since in self.temp_channels.items():
            if now - empty_since >= CHANNEL_TIMEOUT_SECONDS:
                channel = self.bot.get_channel(channel_id)
                if channel and len(channel.members) == 0:
                    try:
                        await channel.delete(reason="Temporary VC expired")
                        to_delete.append(channel_id)
                    except Exception as e:
                        print(f"Failed to delete channel {channel_id}: {e}")
                        to_delete.append(channel_id)
        for cid in to_delete:
            self.temp_channels.pop(cid, None)

    @cleanup_task.before_loop
    async def before_cleanup(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(VoiceManager(bot))
