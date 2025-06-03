import discord
from discord.ext import commands
from cogs.config_store import (
    init_settings,
    get_setting,
    set_setting
)
from cogs.stats_store import (
    init_stats,
    get_stat,
    set_stat,
    increment_stat,
    get_user_stat,
    set_user_stat,
    increment_user_stat,
)

class CountingGame(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        init_settings()
        init_stats()
        self.last_user_id = None

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        counting_channel_id = int(get_setting("counting_channel_id", 0) or 0)
        if message.channel.id != counting_channel_id:
            return

        if bool(int(get_setting("counting_paused", 0) or 0)):
            return

        allow_chat = bool(int(get_setting("allow_chat_between_counts", 0) or 0))
        current_count = int(get_setting("current_count", 0) or 0)

        content = message.content.strip()
        if not content.isdigit():
            if not allow_chat and current_count != 0:
                await self.fail(message.channel, message.author, "sent a non-number!")
            return

        number = int(content)

        if current_count == 0:
            if number == 1:
                self.last_user_id = message.author.id
                set_setting("current_count", 1)
                await self.react_to_count(message, 1)
                increment_stat("total_counts")
                increment_user_stat("personal_count", message.author.id)
                set_user_stat("high", message.author.id, 1)
                if get_stat("high_count", 0) < 1:
                    set_stat("high_count", 1)
                return
            else:
                await self.fail(message.channel, message.author, f"started with **{number}** instead of **1**.")
                return

        expected = current_count + 1

        if message.author.id == self.last_user_id:
            await self.fail(message.channel, message.author, "counted twice in a row!")
            return

        if number != expected:
            await self.fail(message.channel, message.author, f"counted **{number}**, expected **{expected}**.")
            return

        self.last_user_id = message.author.id
        set_setting("current_count", expected)

        await self.react_to_count(message, expected)

        increment_stat("total_counts")
        increment_user_stat("personal_count", message.author.id)

        if expected > get_user_stat("high", message.author.id, 0):
            set_user_stat("high", message.author.id, expected)

        if expected > get_stat("high_count", 0):
            set_stat("high_count", expected)

    async def fail(self, channel: discord.TextChannel, user: discord.User, reason: str):
        await channel.send(f"❌ {user.mention} {reason} Count reset to 0.")
        set_setting("current_count", 0)
        self.last_user_id = None
        increment_user_stat("fail", user.id)

    async def react_to_count(self, message: discord.Message, count: int):
        # React based on count ranges
        if count % 100 == 0:
            await message.add_reaction("🎉")
            await message.channel.send(f"🎉 Milestone! We've reached **{count}**!")
        else:
            rem = count % 500
            if rem < 100:
                await message.add_reaction("✅")
            elif rem < 200:
                await message.add_reaction("☑️")
            elif rem < 300:
                await message.add_reaction("🔥")
            elif rem < 400:
                await message.add_reaction("❤️‍🔥")
            else:
                await message.add_reaction("🌟")

async def setup(bot: commands.Bot):
    await bot.add_cog(CountingGame(bot))
