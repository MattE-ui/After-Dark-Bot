import discord
from discord.ext import commands
from discord.utils import get
import datetime
import os

auto_bump_enabled = False

class Bump(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        global auto_bump_enabled
        if message.author == self.bot.user or not auto_bump_enabled:
            return

        bump_reminder_role = get(message.guild.roles, name="Bump Reminder")
        if not bump_reminder_role:
            return

        if bump_reminder_role in message.role_mentions:
            bump_channel = discord.utils.get(message.guild.text_channels, name="﹐bump")
            if bump_channel:
                try:
                    await bump_channel.send("/bump")
                    now = datetime.datetime.utcnow()
                    print(f"✅ Auto-bump triggered at {now.isoformat()} UTC in #{bump_channel.name}")
                except discord.Forbidden:
                    print(f"❌ Missing permissions for #{bump_channel.name}")
            else:
                print("❌ Bump channel not found")

    @commands.slash_command(name="toggle_autobump", description="(Developer Only) Toggle auto /bump when reminded")
    async def toggle_autobump(self, ctx):
        # Get developer ID from environment variable
        developer_id = os.getenv("DEVELOPER_ID")
        if not developer_id or str(ctx.author.id) != developer_id:
            await ctx.respond("❌ This command is restricted to the bot developer.", ephemeral=True)
            return

        global auto_bump_enabled
        auto_bump_enabled = not auto_bump_enabled
        status = "enabled" if auto_bump_enabled else "disabled"
        await ctx.respond(f"✅ Auto bumping is now **{status}**.", ephemeral=True)

def setup(bot):
    bot.add_cog(Bump(bot))