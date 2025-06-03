
import discord
from discord.ext import commands
from discord import app_commands
import os
from pathlib import Path

class DevTools(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="reload", description="Reloads bot extensions (cogs).")
    @commands.is_owner()
    async def reload(self, interaction: discord.Interaction):
        COG_EXCLUDES = {"config_store", "stats_store", "__init__"}
        reloaded = []
        failed = []

        for file in Path("./cogs").glob("*.py"):
            name = file.stem
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

        embed = discord.Embed(title="🔄 Reload Results")
        if reloaded:
            embed.add_field(name="✅ Reloaded", value=", ".join(reloaded), inline=False)
        if failed:
            fail_lines = [f"{name}: {err}" for name, err in failed]
            embed.add_field(name="❌ Failed", value="\n".join(fail_lines), inline=False)

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(DevTools(bot))
