from discord import app_commands

import discord
from discord.ext import commands
import json
import os

CONFIG_PATH = "config.json"
STATS_PATH = "counting_stats.json"

def _load_config() -> dict:
    defaults = {
        "welcome_enabled": False,
        "reddit_enabled": True,
        "reddit_channel_id": None,
        "counting_channel_id": None,
        "counting_paused": False,
        "current_count": 0,
        "allow_chat_between_counts": False
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
        self._config = _load_config()
        self._stats = _load_stats()

        self.current_count = self._config.get("current_count", 0)
        self.paused = self._config.get("counting_paused", False)
        self.allow_chat = self._config.get("allow_chat_between_counts", False)
        self.last_user_id = None

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignore bots and DMs
        if message.author.bot or not message.guild:
            return

        # Reload config on each message
        self._config = _load_config()
        self.current_count = self._config.get("current_count", 0)
        self.paused = self._config.get("counting_paused", False)
        self.allow_chat = self._config.get("allow_chat_between_counts", False)
        count_chan_id = self._config.get("counting_channel_id")

        # If paused or no channel set, skip
        if self.paused or not count_chan_id or message.channel.id != count_chan_id:
            return

        content = message.content.strip()
        if not content.isdigit():
            # Non-numeric message
            if not self.allow_chat and self.current_count != 0:
                await self._fail(message.channel, message.author, "sent a non-number! Starting over.")
            return

        number = int(content)

        # Starting new game: expect 1
        if self.current_count == 0:
            if number == 1:
                self.current_count = 1
                self.last_user_id = message.author.id

                # React with ✅ (cycle 1–99)
                await message.add_reaction("✅")
                self._record_success(message.author.id, 1)
                self._update_high_global(1)

                # Save new count
                self._config["current_count"] = 1
                _save_config(self._config)
                return
            else:
                await self._fail(
                    message.channel,
                    message.author,
                    f"tried to start with **{number}** instead of **1**."
                )
                return

        # Otherwise, expect current_count + 1
        expected = self.current_count + 1

        # Same user twice?
        if message.author.id == self.last_user_id:
            await self._fail(message.channel, message.author, "counted twice in a row! Starting over.")
            return

        # Wrong number?
        if number != expected:
            await self._fail(
                message.channel,
                message.author,
                f"counted **{number}**, but expected **{expected}**."
            )
            return

        # Correct next number
        self.current_count = expected
        self.last_user_id = message.author.id

        # Update persistent config
        self._config["current_count"] = self.current_count
        _save_config(self._config)

        # Add reaction based on the number
        num = self.current_count
        if num % 100 == 0:
            await message.add_reaction("🎉")
            # Announce milestone
            await message.channel.send(f"🎉 We've reached **{num}**! Keep it going!")
        else:
            rem = num % 500
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

        # Record stats
        self._record_success(message.author.id, self.current_count)
        self._update_high_global(self.current_count)

    def _record_success(self, user_id: int, number_reached: int):
        tot = self._stats["total_counts"].get(str(user_id), 0) + 1
        self._stats["total_counts"][str(user_id)] = tot

        prev_high = self._stats["user_highs"].get(str(user_id), 0)
        if number_reached > prev_high:
            self._stats["user_highs"][str(user_id)] = number_reached

        _save_stats(self._stats)

    def _update_high_global(self, number_reached: int):
        prev_high = self._stats.get("high_count", 0)
        if number_reached > prev_high:
            self._stats["high_count"] = number_reached
            _save_stats(self._stats)

    async def _fail(self, channel: discord.TextChannel, user: discord.Member, reason: str):
        fails = self._stats["fail_counts"].get(str(user.id), 0) + 1
        self._stats["fail_counts"][str(user.id)] = fails
        _save_stats(self._stats)

        await channel.send(f"❌ {user.mention} {reason}")

        # Reset the count
        self.current_count = 0
        self.last_user_id = None
        self._config["current_count"] = 0
        _save_config(self._config)

    # ─── ADMIN SLASH COMMANDS ──────────────────────────────────────────────────

    @app_commands.command(name="pause_counting", description="Pause the counting game (Admin only).")
    async def pause_counting(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You must be an admin to use this.", ephemeral=True)
            return

        self._config["counting_paused"] = True
        _save_config(self._config)
        await interaction.response.send_message(
            f"⏸️ Counting game paused. Current count: **{self._config['current_count']}**."
        )

    @app_commands.command(name="resume_counting", description="Resume the counting game (Admin only).")
    async def resume_counting(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You must be an admin to use this.", ephemeral=True)
            return

        self._config["counting_paused"] = False
        _save_config(self._config)
        await interaction.response.send_message("▶️ Counting game resumed.")

    @app_commands.command(name="restore_count", description="Set the count to a specific number (Admin only).")
    @app_commands.describe(number="Number to set as current count")
    async def restore_count(self, interaction: discord.Interaction, number: int):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You must be an admin to use this.", ephemeral=True)
            return

        if number < 0:
            await interaction.response.send_message("❌ Please give a non-negative integer.", ephemeral=True)
            return

        self._config["current_count"] = number
        _save_config(self._config)
        await interaction.response.send_message(
            f"✅ Count set to **{number}**. Next expected: {number + 1}."
        )

    @app_commands.command(name="skip_to_count", description="Skip count to a specific number (Admin only).")
    @app_commands.describe(number="Number to skip to (must be ≥ current_count+1)")
    async def skip_to_count(self, interaction: discord.Interaction, number: int):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You must be an admin to use this.", ephemeral=True)
            return

        current = self._config.get("current_count", 0)
        if number < current + 1:
            await interaction.response.send_message(
                f"❌ Cannot skip to less than {current + 1}. Current: {current}.",
                ephemeral=True
            )
            return

        self._config["current_count"] = number
        _save_config(self._config)
        await interaction.response.send_message(
            f"✅ Skipped to **{number}**. Next expected: {number + 1}."
        )

    @app_commands.command(name="toggle_chat_between_counts", description="Allow or disallow messages between counts (Admin only).")
    async def toggle_chat_between_counts(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You must be an admin to use this.", ephemeral=True)
            return

        current = self._config.get("allow_chat_between_counts", False)
        self._config["allow_chat_between_counts"] = not current
        _save_config(self._config)
        state = "enabled" if self._config["allow_chat_between_counts"] else "disabled"
        await interaction.response.send_message(f"💬 Chat between counts is now **{state}**.")

    @app_commands.command(name="view_stats", description="View counting stats.")
    async def view_stats(self, interaction: discord.Interaction):
        # Available to everyone, sends publicly
        stats = _load_stats()
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

        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    existing = bot.get_cog("CountingGame")
    if existing:
        await bot.remove_cog("CountingGame")
    await bot.add_cog(CountingGame(bot))
