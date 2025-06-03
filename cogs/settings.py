import discord
from discord.ext import commands
from discord import app_commands
import os

# Import our SQLite helpers
from cogs.config_store import get_setting, set_setting
from cogs.stats_store import (
    get_stat,
    set_stat,
    increment_stat,
    get_user_stat,
    set_user_stat,
    increment_user_stat,
    top_user_stats
)


class Settings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ─── COUNTING CHANNEL SETUP ─────────────────────────────────────────────────

    @app_commands.command(
        name="set_counting_channel",
        description="Set the text channel where the counting game occurs."
    )
    @app_commands.describe(channel="The channel to use for counting")
    @commands.has_permissions(administrator=True)
    async def set_counting_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        set_setting("counting_channel_id", channel.id)
        await interaction.response.send_message(
            f"✅ Counting channel set to {channel.mention}.",
            ephemeral=True
        )

    # ─── REDDIT CHANNEL SETUP ───────────────────────────────────────────────────

    @app_commands.command(
        name="set_reddit_channel",
        description="Set the text channel where Reddit posts are mirrored."
    )
    @app_commands.describe(channel="The channel to send Reddit mirrors")
    @commands.has_permissions(administrator=True)
    async def set_reddit_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        set_setting("reddit_channel_id", channel.id)
        await interaction.response.send_message(
            f"📨 Reddit posts will now be mirrored to {channel.mention}.",
            ephemeral=True
        )

    # ─── TOGGLE REDDIT MIRRORING ────────────────────────────────────────────────

    @app_commands.command(
        name="toggle_reddit",
        description="Enable or disable automatic Reddit mirroring."
    )
    @commands.has_permissions(administrator=True)
    async def toggle_reddit(self, interaction: discord.Interaction):
        current = bool(int(get_setting("reddit_enabled", 1)))
        new_val = int(not current)
        set_setting("reddit_enabled", new_val)
        status = "enabled" if not current else "disabled"
        await interaction.response.send_message(
            f"🔁 Reddit mirroring is now **{status}**.",
            ephemeral=True
        )

    # ─── CHAT-BETWEEN-COUNTS TOGGLE ─────────────────────────────────────────────

    @app_commands.command(
        name="toggle_chat_between_counts",
        description="Allow or disallow non-number messages between counts."
    )
    @commands.has_permissions(administrator=True)
    async def toggle_chat_between_counts(self, interaction: discord.Interaction):
        current = bool(int(get_setting("allow_chat_between_counts", 0)))
        new_val = int(not current)
        set_setting("allow_chat_between_counts", new_val)
        status = "allowed" if not current else "disallowed"
        await interaction.response.send_message(
            f"💬 Chat between counts is now **{status}**.",
            ephemeral=True
        )

    # ─── PAUSE / RESUME COUNTING ────────────────────────────────────────────────

    @app_commands.command(
        name="pause_counting",
        description="Pause the counting game (no one can count until resumed)."
    )
    @commands.has_permissions(administrator=True)
    async def pause_counting(self, interaction: discord.Interaction):
        set_setting("counting_paused", 1)
        current_count = get_setting("current_count", 0)
        await interaction.response.send_message(
            f"⏸️ Counting game paused at **{current_count}**.",
            ephemeral=True
        )

    @app_commands.command(
        name="resume_counting",
        description="Resume the counting game after a pause."
    )
    @commands.has_permissions(administrator=True)
    async def resume_counting(self, interaction: discord.Interaction):
        set_setting("counting_paused", 0)
        await interaction.response.send_message(
            "▶️ Counting game resumed.",
            ephemeral=True
        )

    # ─── RESTORE / SKIP-TO COUNTS ─────────────────────────────────────────────────

    @app_commands.command(
        name="restore_count",
        description="Set the count to a specific number immediately."
    )
    @app_commands.describe(number="The number to set as the current count")
    @commands.has_permissions(administrator=True)
    async def restore_count(self, interaction: discord.Interaction, number: int):
        if number < 0:
            await interaction.response.send_message(
                "❌ Count must be a non-negative integer.",
                ephemeral=True
            )
            return

        set_setting("current_count", number)
        await interaction.response.send_message(
            f"✅ Count set to **{number}**. Next expected: {number + 1}.",
            ephemeral=True
        )

    @app_commands.command(
        name="skip_to_count",
        description="Skip the count forward to a higher number (must be ≥ current+1)."
    )
    @app_commands.describe(number="Number to skip to (must be ≥ current_count+1)")
    @commands.has_permissions(administrator=True)
    async def skip_to_count(self, interaction: discord.Interaction, number: int):
        current = int(get_setting("current_count", 0))
        if number < current + 1:
            await interaction.response.send_message(
                f"❌ Cannot skip to less than **{current + 1}**. Current: {current}.",
                ephemeral=True
            )
            return

        set_setting("current_count", number)
        await interaction.response.send_message(
            f"✅ Count skipped to **{number}**. Next expected: {number + 1}.",
            ephemeral=True
        )

    # ─── VIEW STATS ─────────────────────────────────────────────────────────────

    @app_commands.command(
        name="view_stats",
        description="View counting statistics (high scores, failures, etc.)."
    )
    async def view_stats(self, interaction: discord.Interaction):
        # Retrieve stats from SQLite
        high_count = get_stat("high_count", 0)

        # Top 5 personal highs
        top_personal = top_user_stats("high", 5)
        desc_highs = "\n".join(f"<@{uid}>: {val}" for uid, val in top_personal) or "None"

        # Top 5 total contributors
        top_contrib = top_user_stats("personal_count", 5)
        desc_contrib = "\n".join(f"<@{uid}>: {val}" for uid, val in top_contrib) or "None"

        # Top 5 failures
        top_fails = top_user_stats("fail", 5)
        desc_fails = "\n".join(f"<@{uid}>: {val}" for uid, val in top_fails) or "None"

        embed = discord.Embed(
            title="Counting Game Statistics",
            color=discord.Color.green()
        )
        embed.add_field(name="🔢 Global High Count", value=str(high_count), inline=False)
        embed.add_field(name="🏆 Top 5 Personal Highs", value=desc_highs, inline=False)
        embed.add_field(name="🔁 Top 5 Contributors", value=desc_contrib, inline=False)
        embed.add_field(name="❌ Top 5 Failures", value=desc_fails, inline=False)

        await interaction.response.send_message(embed=embed)

    # ─── WELCOME MESSAGE TOGGLES ────────────────────────────────────────────────

    @app_commands.command(
        name="toggle_welcome",
        description="(Developer Only) Enable or disable welcome messages."
    )
    async def toggle_welcome(self, interaction: discord.Interaction):
        developer_id = os.getenv("DEVELOPER_ID")
        if not developer_id or str(interaction.user.id) != developer_id:
            await interaction.response.send_message("❌ Developer only.", ephemeral=True)
            return

        current = bool(int(get_setting("welcome_enabled", 0)))
        new_val = int(not current)
        set_setting("welcome_enabled", new_val)
        state = "enabled" if not current else "disabled"
        await interaction.response.send_message(
            f"👋 Welcome messages are now **{state}**.",
            ephemeral=True
        )

    @app_commands.command(
        name="test_welcome",
        description="(Developer Only) Send a test welcome DM or fallback message."
    )
    async def test_welcome(self, interaction: discord.Interaction):
        developer_id = os.getenv("DEVELOPER_ID")
        if not developer_id or str(interaction.user.id) != developer_id:
            await interaction.response.send_message("❌ Developer only.", ephemeral=True)
            return

        from cogs.welcome import GameRoleSelection

        view = GameRoleSelection(interaction.user.id)
        await interaction.response.send_message(
            f"🎉 Welcome to the server, {interaction.user.mention}!\n\nSelect your game below:",
            view=view,
            ephemeral=True
        )

    # ─── DEVELOPER COG MANAGEMENT ───────────────────────────────────────────────

    @app_commands.command(
        name="reload_cogs",
        description="(Developer Only) Reload all or a specific cog."
    )
    @app_commands.describe(cog="Name of the cog to reload (optional)")
    async def reload_cogs(self, interaction: discord.Interaction, cog: str = None):
        developer_id = os.getenv("DEVELOPER_ID")
        if not developer_id or str(interaction.user.id) != developer_id:
            await interaction.response.send_message("❌ Developer only.", ephemeral=True)
            return

        reloaded = []
        failed = []

        if cog:
            # Reload a single cog
            if cog in {"config_store", "stats_store", "__init__"}:
                await interaction.response.send_message(
                    f"⚠️ `{cog}` is not a cog and cannot be reloaded.",
                    ephemeral=True
                )
                return

            ext = f"cogs.{cog}"
            try:
                await self.bot.reload_extension(ext)
                reloaded.append(cog)
            except commands.ExtensionNotLoaded:
                try:
                    await self.bot.load_extension(ext)
                    reloaded.append(cog)
                except Exception as e:
                    failed.append((cog, str(e)))
            except Exception as e:
                failed.append((cog, str(e)))
        else:
            # Reload all cogs except helper modules
            COG_EXCLUDES = {"config_store.py", "stats_store.py", "__init__.py"}
            for file in os.listdir("./cogs"):
                if not file.endswith(".py") or file in COG_EXCLUDES:
                    continue

                name = file[:-3]
                ext = f"cogs.{name}"
                try:
                    await self.bot.reload_extension(ext)
                    reloaded.append(name)
                except commands.ExtensionNotLoaded:
                    try:
                        await self.bot.load_extension(ext)
                        reloaded.append(name)
                    except Exception as e:
                        failed.append((name, str(e)))
                except Exception as e:
                    failed.append((name, str(e)))

        embed = discord.Embed(
            title="🔄 Reload Results",
            color=discord.Color.blurple()
        )
        if reloaded:
            embed.add_field(name="✅ Reloaded", value=", ".join(reloaded), inline=False)
        if failed:
            lines = [f"• **{n}**: {err}" for n, err in failed]
            embed.add_field(name="❌ Failed", value="\n".join(lines), inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="load_cog",
        description="(Developer Only) Load a specific cog."
    )
    @app_commands.describe(cog="Name of the cog to load")
    async def load_cog(self, interaction: discord.Interaction, cog: str):
        developer_id = os.getenv("DEVELOPER_ID")
        if not developer_id or str(interaction.user.id) != developer_id:
            await interaction.response.send_message("❌ Developer only.", ephemeral=True)
            return

        if cog in {"config_store", "stats_store", "__init__"}:
            await interaction.response.send_message(
                f"⚠️ `{cog}` is not a cog and cannot be loaded.",
                ephemeral=True
            )
            return

        ext = f"cogs.{cog}"
        try:
            await self.bot.load_extension(ext)
            await interaction.response.send_message(f"✅ Loaded `{cog}`.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Failed to load `{cog}`:\n```{e}```",
                ephemeral=True
            )

    @app_commands.command(
        name="unload_cog",
        description="(Developer Only) Unload a specific cog."
    )
    @app_commands.describe(cog="Name of the cog to unload")
    async def unload_cog(self, interaction: discord.Interaction, cog: str):
        developer_id = os.getenv("DEVELOPER_ID")
        if not developer_id or str(interaction.user.id) != developer_id:
            await interaction.response.send_message("❌ Developer only.", ephemeral=True)
            return

        if cog in {"config_store", "stats_store", "__init__"}:
            await interaction.response.send_message(
                f"⚠️ `{cog}` is not a cog and cannot be unloaded.",
                ephemeral=True
            )
            return

        ext = f"cogs.{cog}"
        try:
            await self.bot.unload_extension(ext)
            await interaction.response.send_message(
                f"✅ Unloaded `{cog}`.", ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Failed to unload `{cog}`:\n```{e}```",
                ephemeral=True
            )

    @app_commands.command(
        name="list_cogs",
        description="(Developer Only) List all currently loaded cogs."
    )
    async def list_cogs(self, interaction: discord.Interaction):
        developer_id = os.getenv("DEVELOPER_ID")
        if not developer_id or str(interaction.user.id) != developer_id:
            await interaction.response.send_message("❌ Developer only.", ephemeral=True)
            return

        loaded = list(self.bot.extensions.keys())
        if not loaded:
            await interaction.response.send_message(
                "⚠️ No cogs are currently loaded.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "📦 Loaded cogs:\n" + "\n".join(loaded),
                ephemeral=True
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(Settings(bot))
