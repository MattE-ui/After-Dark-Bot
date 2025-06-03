import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import asyncio
import webserver

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = os.getenv("GUILD_ID")  # e.g. "1378789064274350193"

if not TOKEN:
    raise ValueError("DISCORD_TOKEN is missing in the .env file.")

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    """
    Once the bot is ready, sync all slash commands to the guild (if provided),
    or globally if GUILD_ID is None.
    """
    print(f"{bot.user} is connected and ready!")
    print(f"Bot is in {len(bot.guilds)} guild(s)")

    try:
        if GUILD_ID:
            # Copy global commands to the guild and sync
            guild = discord.Object(id=int(GUILD_ID))
            bot.tree.copy_global_to(guild=guild)
            synced = await bot.tree.sync(guild=guild)
            print(f"Synced {len(synced)} command(s) to guild {GUILD_ID}")
        else:
            synced = await bot.tree.sync()
            print(f"Synced {len(synced)} global command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

async def load_cogs():
    """
    Load each .py file in cogs/, skipping helper modules that are NOT true cogs:
    - config_store.py
    - stats_store.py
    - __init__.py
    """
    COG_EXCLUDES = {"config_store.py", "stats_store.py", "__init__.py"}
    for filename in os.listdir("./cogs"):
        if not filename.endswith(".py"):
            continue
        if filename in COG_EXCLUDES:
            continue

        cog_name = filename[:-3]  # e.g. "counting_game"
        try:
            await bot.load_extension(f"cogs.{cog_name}")
            print(f"Loaded cog: cogs.{cog_name}")
        except Exception as e:
            print(f"Failed to load cog {filename}: {e}")

async def main():
    async with bot:
        await load_cogs()
        await bot.start(TOKEN)

# Start the tiny Flask server to keep the bot alive (e.g. on Render/Replit)
webserver.keep_alive()

if __name__ == "__main__":
    asyncio.run(main())
