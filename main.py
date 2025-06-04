# main.py

import os
import logging
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = os.getenv("GUILD_ID")
SYNC_MODE = os.getenv("SYNC_MODE", "global").lower()

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@bot.event
async def on_ready():
    print(f"🤖 Logged in as {bot.user} ({bot.user.id})")
    print(f"🔧 Sync mode: {SYNC_MODE}")

    try:
        if SYNC_MODE == "dev" and GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))
            synced = await bot.tree.sync(guild=guild)
            logger.info(f"🧪 Synced {len(synced)} slash command(s) to dev guild {guild.id}.")
            print(f"🧪 Synced {len(synced)} slash command(s) to dev guild {guild.id}.\n")
        else:
            synced = await bot.tree.sync()
            logger.info(f"🌍 Synced {len(synced)} slash command(s) globally.")
            print(f"🌍 Synced {len(synced)} slash command(s) globally.\n")
    except Exception as e:
        logger.error(f"❌ Slash command sync failed: {e}")
        print(f"❌ Slash command sync failed: {e}\n")


@bot.event
async def setup_hook():
    from pathlib import Path

    cog_folder = Path("./cogs")
    for file in cog_folder.glob("*.py"):
        if file.name.startswith("_"):
            continue
        try:
            await bot.load_extension(f"cogs.{file.stem}")
            print(f"✅ Loaded cog: {file.stem}")
        except Exception as e:
            print(f"❌ Failed to load cog {file.stem}: {e}")


if __name__ == "__main__":
    bot.run(TOKEN)
