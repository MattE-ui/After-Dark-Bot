
import discord
from discord.ext import commands, tasks
import time

# Name of the voice channel users join to create their own
CREATE_VC_CHANNEL_NAME = "₊ Join to Create"

# Number of seconds a channel must stay empty before deletion
EMPTY_TIMEOUT = 120  # 2 minutes

class VoiceManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Tracks temporary channels: channel_id -> timestamp_when_empty
        self.temp_channels = {}
        self.cleanup_task.start()

    def cog_unload(self):
        self.cleanup_task.cancel()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        # If user joined the create channel
        if after.channel and after.channel.name == CREATE_VC_CHANNEL_NAME:
            guild = member.guild
            parent = after.channel.category
            new_channel_name = f"{member.display_name}'s Channel"
            # Overwrites: everyone can connect, but owner has manage permissions
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(connect=True),
                member: discord.PermissionOverwrite(manage_channels=True, manage_permissions=True, connect=True)
            }
            new_channel = await guild.create_voice_channel(
                name=new_channel_name,
                overwrites=overwrites,
                category=parent
            )
            await member.move_to(new_channel)
            self.temp_channels[new_channel.id] = None

        # If user left a temp channel
        if before.channel and before.channel.id in self.temp_channels:
            if len(before.channel.members) == 0:
                if self.temp_channels[before.channel.id] is None:
                    self.temp_channels[before.channel.id] = time.time()
            else:
                self.temp_channels[before.channel.id] = None

    @tasks.loop(seconds=60.0)
    async def cleanup_task(self):
        to_remove = []
        for chan_id, empty_since in list(self.temp_channels.items()):
            channel = self.bot.get_channel(chan_id)
            if channel is None:
                to_remove.append(chan_id)
                continue
            if len(channel.members) == 0:
                if empty_since is None:
                    self.temp_channels[chan_id] = time.time()
                else:
                    if time.time() - empty_since >= EMPTY_TIMEOUT:
                        try:
                            await channel.delete()
                        except Exception:
                            pass
                        to_remove.append(chan_id)
            else:
                self.temp_channels[chan_id] = None

        for rid in to_remove:
            del self.temp_channels[rid]

    @cleanup_task.before_loop
    async def before_cleanup(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(VoiceManager(bot))
