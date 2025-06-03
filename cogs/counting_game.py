import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from cogs.config_store import init_settings, get_setting, set_setting

STATS_PATH = "counting_stats.json"

def _load_stats() -> dict:
    defaults = {
        "high_count": 0,
        "user_highs": {},
        "total_counts": {},
        "fail_counts": {}
    }
    if not os.path.exists(STATS_PATH):
        with open(STATS_PATH, "w") as f:
            json.dump(defaults, f, indent=4)
        return defaults

    with open(STATS_PATH, "r") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            data = defaults

    for key, val in defaults.items():
        if key not in data:
            data[key] = val

    return data

def _save_stats(stats: dict):
    with open(STATS_PATH, "w") as f:
        json.dump(stats, f, indent=4)

class CountingGame(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        init_settings()
        self._stats = _load_stats()
        self.last_user_id = None

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        counting_paused = bool(int(get_setting("counting_paused", 0)))
        allow_chat = bool(int(get_setting("allow_chat_between_counts", 0)))
        channel_id = int(get_setting("counting_channel_id", 0))
        current_count = int(get_setting("current_count", 0))

        if counting_paused or message.channel.id != channel_id:
            return

        content = message.content.strip()
        if not content.isdigit():
            if not allow_chat and current_count != 0:
                await self._fail(message.channel, message.author, "sent a non-number! Starting over.")
            return

        number = int(content)

        if current_count == 0:
            if number == 1:
                self.last_user_id = message.author.id
                set_setting("current_count", 1)
                await message.add_reaction("✅")
                self._record_success(message.author.id, 1)
                self._update_high_global(1)
                return
            else:
                await self._fail(message.channel, message.author, f"tried to start with **{number}** instead of **1**.")
                return

        expected = current_count + 1

        if message.author.id == self.last_user_id:
            await self._fail(message.channel, message.author, "counted twice in a row! Starting over.")
            return

        if number != expected:
            await self._fail(message.channel, message.author, f"counted **{number}**, but expected **{expected}**.")
            return

        # Valid count
        self.last_user_id = message.author.id
        set_setting("current_count", expected)

        if expected % 100 == 0:
            await message.add_reaction("🎉")
            await message.channel.send(f"🎉 We've reached **{expected}**! Keep it going!")
        else:
            rem = expected % 500
            grp = rem // 100
            reactions = ["✅", "☑️", "🔥", "❤️‍🔥", "🌟"]
            await message.add_reaction(reactions[grp % len(reactions)])

        self._record_success(message.author.id, expected)
        self._update_high_global(expected)

    def _record_success(self, user_id: int, number_reached: int):
        stats = self._stats
        uid = str(user_id)
        stats["total_counts"][uid] = stats["total_counts"].get(uid, 0) + 1

        if number_reached > stats["user_highs"].get(uid, 0):
            stats["user_highs"][uid] = number_reached

        _save_stats(stats)

    def _update_high_global(self, number_reached: int):
        if number_reached > self._stats.get("high_count", 0):
            self._stats["high_count"] = number_reached
            _save_stats(self._stats)

    async def _fail(self, channel: discord.TextChannel, user: discord.Member, reason: str):
        uid = str(user.id)
        self._stats["fail_counts"][uid] = self._stats["fail_counts"].get(uid, 0) + 1
        _save_stats(self._stats)

        await channel.send(f"❌ {user.mention} {reason}")
        set_setting("current_count", 0)
        self.last_user_id = None

async def setup(bot):
    await bot.add_cog(CountingGame(bot))
