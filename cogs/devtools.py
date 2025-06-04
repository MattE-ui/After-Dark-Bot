# cogs/devtools.py

import discord
from discord.ext import commands
from discord import app_commands
import os
from dotenv import load_dotenv
import traceback

load_dotenv()
DEVELOPER_ID = int(os.getenv("DEVELOPER_ID"))
GUILD_ID = int(os.getenv("GUILD_ID"))

class DevTools(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def is_developer(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == DEVELOPER_ID

    @app_commands.command(name="sync", description="(DEV ONLY) 🔁 Sync all slash commands globally.")
    async def sync(self, interaction: discord.Interaction):
        if not self.is_developer(interaction):
            return await interaction.response.send_message("❌ You are not authorized to use this.", ephemeral=True)
        await self.bot.tree.sync()
        await interaction.response.send_message("✅ Slash commands synced.", ephemeral=True)

    @app_commands.command(name="eval", description="(DEV ONLY) ⚙️ Evaluate a Python expression.")
    @app_commands.describe(code="The Python code to evaluate")
    async def eval_command(self, interaction: discord.Interaction, code: str):
        if not self.is_developer(interaction):
            return await interaction.response.send_message("❌ You are not authorized to use this.", ephemeral=True)

        try:
            result = eval(code)
            await interaction.response.send_message(f"🧪 Result: `{result}`", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"⚠️ Error: `{e}`", ephemeral=True)

    @app_commands.command(name="reload_cog", description="(DEV ONLY) ♻️ Reload a specific cog by name.")
    @app_commands.describe(cog="Name of the cog (e.g. counting_game)")
    async def reload_cog(self, interaction: discord.Interaction, cog: str):
        if not self.is_developer(interaction):
            return await interaction.response.send_message("❌ You are not authorized to use this.", ephemeral=True)

        try:
            await self.bot.reload_extension(f"cogs.{cog}")
            await interaction.response.send_message(f"✅ Reloaded cog: `{cog}`", ephemeral=True)
        except Exception as e:
            traceback_str = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
            await interaction.response.send_message(f"❌ Failed to reload cog `{cog}`:\n```{traceback_str[:1900]}```", ephemeral=True)

    @app_commands.command(name="clear_commands", description="(DEV ONLY) 🧹 Clear slash commands from this dev server only.")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def clear_commands(self, interaction: discord.Interaction):
        if not self.is_developer(interaction):
            return await interaction.response.send_message("❌ Unauthorized", ephemeral=True)

        try:
            guild = discord.Object(id=interaction.guild_id)
            self.bot.tree.clear_commands(guild=guild)
            await self.bot.tree.sync(guild=guild)
            await interaction.response.send_message("🧹 Slash commands cleared from this dev server.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to clear commands: {e}", ephemeral=True)

    @app_commands.command(name="clear_global_commands", description="(DEV ONLY) 🚨 Clear all global slash commands (use cautiously).")
    async def clear_global_commands(self, interaction: discord.Interaction):
        if not self.is_developer(interaction):
            return await interaction.response.send_message("❌ Unauthorized", ephemeral=True)

        try:
            self.bot.tree.clear_commands(guild=None)
            await self.bot.tree.sync()
            await interaction.response.send_message("🌍 Cleared all global slash commands.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to clear global commands: {e}", ephemeral=True)

    @app_commands.command(name="devtest", description="(DEV ONLY) Test if devtools slash commands are registering.")
    async def devtest(self, interaction: discord.Interaction):
        await interaction.response.send_message("✅ Devtools is registering correctly!", ephemeral=True)


async def setup(bot):
    await bot.add_cog(DevTools(bot))
