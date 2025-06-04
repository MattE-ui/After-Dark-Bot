# cogs/counting_game.py

import discord
from discord.ext import commands
from discord import app_commands

from database.config_store import get_config, set_config
from database.stats_store import get_user_stat, increment_user_stat

class CountingGame(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # Updated emoji cycle
        self.EMOJI_CYCLE = ["✅", "☑️", "🔥", "❤️‍🔥", "🌟"]

    def get_cycle_emoji(self, count: int) -> str:
        index = (count // 100) % len(self.EMOJI_CYCLE)
        return self.EMOJI_CYCLE[index]

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        counting_channel_id = get_config("counting_channel_id")
        if not counting_channel_id or message.channel.id != int(counting_channel_id):
            return

        if get_config("counting_paused"):
            return

        allow_chat = get_config("allow_chat_between_counts") or False
        content = message.content.strip()

        if not content.isdigit() and not allow_chat:
            await message.delete()
            return

        if content.isdigit():
            user_id = message.author.id
            current_count = get_config("current_count") or 0
            expected_count = current_count + 1
            last_user_id = get_config("last_counter_id")

            try:
                user_count = int(content)
            except ValueError:
                return

            if user_count != expected_count or user_id == last_user_id:
                await message.add_reaction("💥")
                await message.channel.send(
                    f"❌ {message.author.mention} broke the count at `{user_count}`. Start again from 1!",
                    delete_after=6
                )
                set_config("current_count", 0)
                set_config("last_counter_id", None)
                return

            # ✅ Correct count
            reaction_emoji = self.get_cycle_emoji(expected_count)
            await message.add_reaction(reaction_emoji)

            set_config("current_count", user_count)
            set_config("last_counter_id", user_id)
            increment_user_stat(user_id, "counting_score")

            # 🎉 Celebration message on each 100th count
            if user_count % 100 == 0:
                await message.channel.send(
                    f"🎉 Congratulations! We've hit **{user_count}**! Keep it going! 🎉",
                    delete_after=10
                )

    @app_commands.command(name="pause_counting", description="(ADMIN ONLY) Pause the counting game.")
    @app_commands.checks.has_permissions(administrator=True)
    async def pause_counting(self, interaction: discord.Interaction):
        set_config("counting_paused", True)
        await interaction.response.send_message("⏸️ Counting has been paused.", ephemeral=True)

    @app_commands.command(name="resume_counting", description="(ADMIN ONLY) Resume the counting game.")
    @app_commands.checks.has_permissions(administrator=True)
    async def resume_counting(self, interaction: discord.Interaction):
        set_config("counting_paused", False)
        await interaction.response.send_message("▶️ Counting has been resumed.", ephemeral=True)

    @app_commands.command(name="counting_stats", description="Show your total counting score.")
    async def counting_stats(self, interaction: discord.Interaction):
        score = get_user_stat(interaction.user.id, "counting_score")
        await interaction.response.send_message(f"🧮 {interaction.user.mention}, your counting score is `{score}`!")

async def setup(bot):
    await bot.add_cog(CountingGame(bot))
