import discord
from discord.ext import commands
from discord import app_commands
from cogs.config_store import get_setting, set_setting
import os

class Settings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # No additional initialization required here

    # ─── COUNTING CHANNEL SETUP ─────────────────────────────────────────────────

    @app_commands.command(
        name="set_counting_channel",
        description="Set the channel where the counting game will occur."
    )
    @app_commands.describe(channel="The text channel for counting")
    @commands.has_permissions(administrator=True)
    async def set_counting_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        set_setting("counting_channel_id", channel.id)
        await interaction.response.send_message(
            f"✅ Counting channel set to {channel.mention}.", 
            ephemeral=True
        )

    # ─── REDDIT CHANNEL SETUP ──────────────────────────────────────────────────

    @app_commands.command(
        name="set_reddit_channel",
        description="Set the channel where Reddit posts will be mirrored."
    )
    @app_commands.describe(channel="The text channel for Reddit mirrors")
    @commands.has_permissions(administrator=True)
    async def set_reddit_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        set_setting("reddit_channel_id", channel.id)
        await interaction.response.send_message(
            f"📨 Reddit posts will now be sent to {channel.mention}.", 
            ephemeral=True
        )

    # ─── TOGGLE REDDIT MIRRORING ────────────────────────────────────────────────

    @app_commands.command(
        name="toggle_reddit",
        description="Enable or disable Reddit mirroring."
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

    # ─── CHAT‐BETWEEN‐COUNTS TOGGLE ──────────────────────────────────────────────

    @app_commands.command(
        name="toggle_chat_between_counts",
        description="Allow or disallow non‐number messages between counts."
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
        description="Pause the counting game (no one can count while paused)."
    )
    @commands.has_permissions(administrator=True)
    async def pause_counting(self, interaction: discord.Interaction):
        set_setting("counting_paused", 1)
        await interaction.response.send_message(
            f"⏸️ Counting game paused. (Current count: {get_setting('current_count', 0)})", 
            ephemeral=True
        )

    @app_commands.command(
        name="resume_counting",
        description="Resume the counting game after being paused."
    )
    @commands.has_permissions(administrator=True)
    async def resume_counting(self, interaction: discord.Interaction):
        set_setting("counting_paused", 0)
        await interaction.response.send_message(
            "▶️ Counting game resumed.", 
            ephemeral=True
        )

    # ─── RESTORE / SKIP‐TO COUNTS ─────────────────────────────────────────────────

    @app_commands.command(
        name="restore_count",
        description="Set the count to a specific number immediately."
    )
    @app_commands.describe(number="The number to set as the current count")
    @commands.has_permissions(administrator=True)
    async def restore_count(self, interaction: discord.Interaction, number: int):
        if number < 0:
            await interaction.response.send_message(
                "❌ Count must be a non‐negative integer.", 
                ephemeral=True
            )
            return

        set_setting("current_count", number)
        await interaction.response.send_message(
            f"✅ Count has been restored to **{number}**. Next expected: {number+1}.", 
            ephemeral=True
        )

    @app_commands.command(
        name="skip_to_count",
        description="Skip the count forward to a number (must be ≥ current+1)."
    )
    @app_commands.describe(number="The number to skip to")
    @commands.has_permissions(administrator=True)
    async def skip_to_count(self, interaction: discord.Interaction, number: int):
        current = int(get_setting("current_count", 0))
        if number < current + 1:
            await interaction.response.send_message(
                f"❌ You can only skip to ≥ {current+1}. Current is {current}.", 
                ephemeral=True
            )
            return

        set_setting("current_count", number)
        await interaction.response.send_message(
            f"✅ Count has been skipped to **{number}**. Next expected: {number+1}.", 
            ephemeral=True
        )

    # ─── SHOW SETTINGS ───────────────────────────────────────────────────────────

    @app_commands.command(
        name="show_settings",
        description="Display all current bot configuration values."
    )
    async def show_settings(self, interaction: discord.Interaction):
        # This one is public (not ephemeral) so people can view in channel if needed
        counting_channel = get_setting("counting_channel_id", "Not set")
        reddit_channel = get_setting("reddit_channel_id", "Not set")
        current = get_setting("current_count", 0)
        allowed_chat = bool(int(get_setting("allow_chat_between_counts", 0)))
        reddit_enabled = bool(int(get_setting("reddit_enabled", 1)))
        paused = bool(int(get_setting("counting_paused", 0)))

        msg = (
            f"🔧 **Current Bot Settings**\n"
            f"• **Counting Channel ID:** `{counting_channel}`\n"
            f"• **Reddit Channel ID:** `{reddit_channel}`\n"
            f"• **Current Count:** `{current}`\n"
            f"• **Allow Chat Between Counts:** `{allowed_chat}`\n"
            f"• **Reddit Mirroring Enabled:** `{reddit_enabled}`\n"
            f"• **Counting Paused:** `{paused}`"
        )
        await interaction.response.send_message(msg, ephemeral=False)

    # ─── DEVELOPER‐ONLY: TOGGLE WELCOME + TEST WELCOME ──────────────────────────

    @app_commands.command(
        name="toggle_welcome",
        description="(Developer Only) Enable or disable welcome messages."
    )
    async def toggle_welcome(self, interaction: discord.Interaction):
        developer_id = os.getenv("DEVELOPER_ID")
        if not developer_id or str(interaction.user.id) != developer_id:
            await interaction.response.send_message(
                "❌ This command is restricted to the bot developer.", 
                ephemeral=True
            )
            return

        # We store welcome state in the same settings table under key "welcome_enabled"
        current = bool(int(get_setting("welcome_enabled", 0)))
        new_val = int(not current)
        set_setting("welcome_enabled", new_val)
        state = "enabled" if not current else "disabled"
        await interaction.response.send_message(
            f"✅ Welcome messages are now **{state}**.", 
            ephemeral=True
        )

    @app_commands.command(
        name="test_welcome",
        description="(Developer Only) Test welcome flow via DM or fallback channel."
    )
    async def test_welcome(self, interaction: discord.Interaction):
        developer_id = os.getenv("DEVELOPER_ID")
        if not developer_id or str(interaction.user.id) != developer_id:
            await interaction.response.send_message(
                "❌ This command is restricted to the bot developer.", 
                ephemeral=True
            )
            return

        # Simply replicate what welcome cog does, without touching the toggle flag:
        from cogs.welcome import GameRoleSelection
        view = GameRoleSelection(interaction.user.id)
        await interaction.response.send_message(
            f"🎉 Welcome to the server, {interaction.user.mention}!\n\n"
            "Select your game below:",
            view=view,
            ephemeral=True
        )

    # ─── COG MANAGEMENT (Developer‐Only) ─────────────────────────────────────────

    @app_commands.command(
        name="reload_cogs",
        description="(Developer Only) Reload all or a specific cog extension."
    )
    @app_commands.describe(cog="Name of the cog to reload (optional)")
    async def reload_cogs(self, interaction: discord.Interaction, cog: str = None):
        developer_id = os.getenv("DEVELOPER_ID")
        if not developer_id or str(interaction.user.id) != developer_id:
            await interaction.response.send_message(
                "❌ This command is restricted to the bot developer.", 
                ephemeral=True
            )
            return

        reloaded = []
        failed = []

        if cog:
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
            COG_EXCLUDES = {
                "config_store",
                "stats_store",
                "__init__",
            }
            for file in os.listdir("./cogs"):
                if not file.endswith(".py"):
                    continue
                name = file[:-3]
                if name in COG_EXCLUDES:
                    continue
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

        embed = discord.Embed(title="🔄 Cog Reload Results", color=discord.Color.blue())
        if reloaded:
            embed.add_field(name="✅ Reloaded", value=", ".join(reloaded), inline=False)
        if failed:
            lines = [f"• **{n}**: {err}" for n, err in failed]
            embed.add_field(name="❌ Failed", value="\n".join(lines), inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ─── COG LOAD / UNLOAD / LIST (Developer‐Only) ──────────────────────────────

    @app_commands.command(name="load_cog", description="(Developer Only) Load a specific cog.")
    @app_commands.describe(cog="Name of the cog to load")
    async def load_cog(self, interaction: discord.Interaction, cog: str):
        developer_id = os.getenv("DEVELOPER_ID")
        if not developer_id or str(interaction.user.id) != developer_id:
            await interaction.response.send_message(
                "❌ This command is restricted to the bot developer.", 
                ephemeral=True
            )
            return

        ext = f"cogs.{cog}"
        try:
            await self.bot.load_extension(ext)
            await interaction.response.send_message(
                f"✅ Loaded cog `{cog}`.", 
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Failed to load cog `{cog}`:\n```{e}```", 
                ephemeral=True
            )

    @app_commands.command(name="unload_cog", description="(Developer Only) Unload a specific cog.")
    @app_commands.describe(cog="Name of the cog to unload")
    async def unload_cog(self, interaction: discord.Interaction, cog: str):
        developer_id = os.getenv("DEVELOPER_ID")
        if not developer_id or str(interaction.user.id) != developer_id:
            await interaction.response.send_message(
                "❌ This command is restricted to the bot developer.", 
                ephemeral=True
            )
            return

        ext = f"cogs.{cog}"
        try:
            await self.bot.unload_extension(ext)
            await interaction.response.send_message(
                f"✅ Unloaded cog `{cog}`. ", 
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Failed to unload cog `{cog}`:\n```{e}```", 
                ephemeral=True
            )

    @app_commands.command(
        name="list_cogs",
        description="(Developer Only) List all currently loaded cogs."
    )
    async def list_cogs(self, interaction: discord.Interaction):
        developer_id = os.getenv("DEVELOPER_ID")
        if not developer_id or str(interaction.user.id) != developer_id:
            await interaction.response.send_message(
                "❌ This command is restricted to the bot developer.", 
                ephemeral=True
            )
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
