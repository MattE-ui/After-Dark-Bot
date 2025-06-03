import discord
from discord.ext import commands
from discord import app_commands
import os
from pathlib import Path

class DevTools(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="reload",
        description="(Developer Only) Reload all or a specific cog."
    )
    @app_commands.describe(cog="Name of the cog to reload (omit to reload all)")
    async def reload(self, interaction: discord.Interaction, cog: str = None):
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
                    f"⚠️ `{cog}` is not a cog and cannot be reloaded.", ephemeral=True
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
            # Reload all valid cogs in cogs/
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

        embed = discord.Embed(title="🔄 Reload Results", color=discord.Color.green())
        if reloaded:
            embed.add_field(name="✅ Reloaded", value=", ".join(reloaded), inline=False)
        if failed:
            lines = [f"• **{n}**: {err}" for n, err in failed]
            embed.add_field(name="❌ Failed", value="\n".join(lines), inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="load",
        description="(Developer Only) Load a single cog."
    )
    @app_commands.describe(cog="Name of the cog to load")
    async def load(self, interaction: discord.Interaction, cog: str):
        developer_id = os.getenv("DEVELOPER_ID")
        if not developer_id or str(interaction.user.id) != developer_id:
            await interaction.response.send_message("❌ Developer only.", ephemeral=True)
            return

        if cog in {"config_store", "stats_store", "__init__"}:
            await interaction.response.send_message(
                f"⚠️ `{cog}` is not a cog and cannot be loaded.", ephemeral=True
            )
            return

        ext = f"cogs.{cog}"
        try:
            await self.bot.load_extension(ext)
            await interaction.response.send_message(f"✅ Loaded `{cog}`.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Failed to load `{cog}`:\n```{e}```", ephemeral=True
            )

    @app_commands.command(
        name="unload",
        description="(Developer Only) Unload a single cog."
    )
    @app_commands.describe(cog="Name of the cog to unload")
    async def unload(self, interaction: discord.Interaction, cog: str):
        developer_id = os.getenv("DEVELOPER_ID")
        if not developer_id or str(interaction.user.id) != developer_id:
            await interaction.response.send_message("❌ Developer only.", ephemeral=True)
            return

        if cog in {"config_store", "stats_store", "__init__"}:
            await interaction.response.send_message(
                f"⚠️ `{cog}` is not a cog and cannot be unloaded.", ephemeral=True
            )
            return

        ext = f"cogs.{cog}"
        try:
            await self.bot.unload_extension(ext)
            await interaction.response.send_message(f"✅ Unloaded `{cog}`.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Failed to unload `{cog}`:\n```{e}```", ephemeral=True
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
            await interaction.response.send_message("⚠️ No cogs are currently loaded.", ephemeral=True)
        else:
            await interaction.response.send_message(
                "📦 Loaded cogs:\n" + "\n".join(loaded),
                ephemeral=True
            )

async def setup(bot: commands.Bot):
    await bot.add_cog(DevTools(bot))
