
import os
import discord
from discord.ext import commands
from discord import app_commands

class DevTools(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.developer_id = os.getenv("DEVELOPER_ID")

    async def is_dev(self, interaction: discord.Interaction) -> bool:
        if str(interaction.user.id) != self.developer_id:
            await interaction.response.send_message("❌ This command is restricted to the developer.", ephemeral=True)
            return False
        return True

    @app_commands.command(name="reload", description="Reload a cog or all cogs (developer only).")
    @app_commands.describe(cog="Name of the cog to reload (optional)")
    async def reload(self, interaction: discord.Interaction, cog: str = None):
        if not await self.is_dev(interaction):
            return

        await interaction.response.defer(ephemeral=True)

        if cog:
            try:
                await self.bot.reload_extension(f"cogs.{cog}")
                await interaction.followup.send(f"✅ Reloaded `cogs.{cog}`.")
            except Exception as e:
                await interaction.followup.send(f"❌ Failed to reload `cogs.{cog}`:\n```{e}```")
        else:
            reloaded = []
            failed = []
            for filename in os.listdir("./cogs"):
                if filename.endswith(".py") and not filename.startswith("__"):
                    cog_name = filename[:-3]
                    try:
                        await self.bot.reload_extension(f"cogs.{cog_name}")
                        reloaded.append(cog_name)
                    except Exception as e:
                        failed.append((cog_name, str(e)))
            msg = ""
            if reloaded:
                msg += f"✅ Reloaded: {', '.join(reloaded)}.\n"
            if failed:
                fail_msgs = '\n'.join([f"{c}: {e}" for c, e in failed])
                msg += f"❌ Failed: {fail_msgs}"
            await interaction.followup.send(msg)

    @app_commands.command(name="load", description="Load a cog (developer only).")
    @app_commands.describe(cog="Name of the cog to load")
    async def load(self, interaction: discord.Interaction, cog: str):
        if not await self.is_dev(interaction):
            return

        await interaction.response.defer(ephemeral=True)
        try:
            await self.bot.load_extension(f"cogs.{cog}")
            await interaction.followup.send(f"✅ Loaded `cogs.{cog}`.")
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to load `cogs.{cog}`:\n```{e}```")

    @app_commands.command(name="unload", description="Unload a cog (developer only).")
    @app_commands.describe(cog="Name of the cog to unload")
    async def unload(self, interaction: discord.Interaction, cog: str):
        if not await self.is_dev(interaction):
            return

        await interaction.response.defer(ephemeral=True)
        try:
            await self.bot.unload_extension(f"cogs.{cog}")
            await interaction.followup.send(f"✅ Unloaded `cogs.{cog}`.")
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to unload `cogs.{cog}`:\n```{e}```")

    @app_commands.command(name="list_cogs", description="List all currently loaded cogs (developer only).")
    async def list_cogs(self, interaction: discord.Interaction):
        if not await self.is_dev(interaction):
            return

        loaded = list(self.bot.extensions.keys())
        if loaded:
            await interaction.response.send_message(f"📦 Loaded cogs:\n" + "\n".join(loaded), ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ No cogs are currently loaded.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(DevTools(bot))
