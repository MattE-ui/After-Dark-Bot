import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import asyncio

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = os.getenv("GUILD_ID")

if not TOKEN:
    raise ValueError("DISCORD_TOKEN is missing in the .env file.")

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

debug_guilds = None
if GUILD_ID:
    try:
        debug_guilds = [int(GUILD_ID)]
    except ValueError:
        print(f"Warning: Invalid GUILD_ID '{GUILD_ID}', syncing globally")

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f"{bot.user} is connected and ready!")
    print(f"Bot is in {len(bot.guilds)} guilds")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)" if synced else "Commands synced successfully.")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

async def load_cogs():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py") and not filename.startswith("__"):
            try:
                await bot.load_extension(f"cogs.{filename[:-3]}")
                print(f"Loaded cog: cogs.{filename[:-3]}")
            except Exception as e:
                print(f"Failed to load cog {filename}: {e}")

async def main():
    async with bot:
        await load_cogs()
        await bot.start(TOKEN)

# Run the bot using asyncio to support async cog loading
asyncio.run(main())
