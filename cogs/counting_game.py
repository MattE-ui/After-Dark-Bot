import discord
from discord.ext import commands
from discord import app_commands
from cogs.config_store import init_settings, get_setting, set_setting
from cogs.stats_store import init_stats, increment_stat, get_stat, get_user_stat, increment_user_stat, top_user_stats
import os

class CountingGame(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Ensure both tables exist
        init_settings()
        init_stats()
        self.last_user_id = None

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignore bots or DMs
        if message.author.bot or not message.guild:
            return

        # Fetch and parse settings
        counting_channel = int(get_setting("counting_channel_id", 0) or 0)
        if message.channel.id != counting_channel:
            return  # Not the counting channel

        paused = bool(int(get_setting("counting_paused", 0) or 0))
        if paused:
            return  # Counting is paused

        allow_chat = bool(int(get_setting("allow_chat_between_counts", 0) or 0))
        current_count = int(get_setting("current_count", 0) or 0)

        content = message.content.strip()
        if not content.isdigit():
            # Non‐numeric messages
            if not allow_chat and current_count != 0:
                # Count resets on non‐number if chat is disallowed
                await self._fail(message.channel, message.author, "sent a non-number! Starting over.")
            return

        number = int(content)

        # New game → expect 1
        if current_count == 0:
            if number == 1:
                self.last_user_id = message.author.id
                set_setting("current_count", 1)
                await message.add_reaction("✅")
                increment_stat("total_counts")        # total count events (global stat)
                increment_user_stat("personal_count", message.author.id, 1)
                increment_user_stat("high", message.author.id, 1)  # personal high = 1
                # Global high update
                if get_stat("high_count", 0) < 1:
                    set_setting("high_count", 1)
                    set_stat("high_count", 1)
                return
            else:
                await self._fail(message.channel, message.author, f"tried to start with **{number}** instead of **1**.")
                return

        # Otherwise expect current_count + 1
        expected = current_count + 1

        # Same user twice?
        if message.author.id == self.last_user_id:
            await self._fail(message.channel, message.author, "counted twice in a row! Starting over.")
            return

        # Wrong number?
        if number != expected:
            await self._fail(message.channel, message.author, f"counted **{number}**, but expected **{expected}**.")
            return

        # Correct count
        self.last_user_id = message.author.id
        set_setting("current_count", expected)

        # Emoji reaction logic:
        if expected % 100 == 0:
            await message.add_reaction("🎉")
            await message.channel.send(f"🎉 We've reached **{expected}**! Keep it going!")
        else:
            rem = expected % 500
            grp = rem // 100
            if grp == 0:
                await message.add_reaction("✅")
            elif grp == 1:
                await message.add_reaction("☑️")
            elif grp == 2:
                await message.add_reaction("🔥")
            elif grp == 3:
                await message.add_reaction("❤️‍🔥")
            else:
                await message.add_reaction("🌟")

        # Update stats
        increment_stat("total_counts")
        increment_user_stat("personal_count", message.author.id)
        # If new personal high:
        if expected > get_user_stat("high", message.author.id, 0):
            set_user_stat("high", message.author.id, expected)
        # If new global high:
        if expected > get_stat("high_count", 0):
            set_stat("high_count", expected)

    async def _fail(self, channel: discord.TextChannel, user: discord.Member, reason: str):
        # Record a fail for this user:
        increment_user_stat("fail", user.id)

        # Notify and reset
        await channel.send(f"❌ {user.mention} {reason}")
        set_setting("current_count", 0)
        self.last_user_id = None

async def setup(bot: commands.Bot):
    await bot.add_cog(CountingGame(bot))
