import discord
from discord.ext import commands
from discord.utils import get
from difflib import get_close_matches

# Game name to role mapping
game_role_map = {
    "dune: awakening": "Fremen",
    "dune awakening": "Fremen",
    "dune": "Fremen",
    "division 2": "SHD Agent",
    "division2": "SHD Agent",
    "div2": "SHD Agent",
    "the division 2": "SHD Agent"
}

class Roles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    #@commands.slash_command(name="apply", description="Apply for a game role.")
    async def apply(self, ctx, game: str = discord.Option(description="Which game are you playing?")):
        user_input = game.lower().strip()
        match = get_close_matches(user_input, game_role_map.keys(), n=1, cutoff=0.6)

        if not match:
            await ctx.respond("Game not recognized. Try 'Dune' or 'Division 2'.", ephemeral=True)
            return

        role_name = game_role_map[match[0]]
        role = get(ctx.guild.roles, name=role_name)

        if not role:
            await ctx.respond(f"Role '{role_name}' not found.", ephemeral=True)
            return

        if role in ctx.author.roles:
            await ctx.respond(f"You already have the **{role_name}** role!", ephemeral=True)
            return

        await ctx.author.add_roles(role)
        await ctx.respond(f"✅ You've been given the **{role_name}** role!", ephemeral=True)

    #@commands.slash_command(name="assign_role", description="(Admin) Assign a game role to a member.")
    async def assign_role(
        self,
        ctx,
        user: discord.Member = discord.Option(description="Member to assign role to"),
        game: str = discord.Option(description="Game name")
    ):
        if not ctx.author.guild_permissions.manage_roles:
            await ctx.respond("❌ You need 'Manage Roles' permissions.", ephemeral=True)
            return

        user_input = game.lower().strip()
        match = get_close_matches(user_input, game_role_map.keys(), n=1, cutoff=0.6)

        if not match:
            await ctx.respond("Game not recognized. Use 'Dune' or 'Division 2'.", ephemeral=True)
            return

        role_name = game_role_map[match[0]]
        role = get(ctx.guild.roles, name=role_name)

        if not role:
            await ctx.respond(f"❌ Role '{role_name}' not found.", ephemeral=True)
            return

        await user.add_roles(role)
        await ctx.respond(f"✅ Assigned **{role_name}** role to {user.mention}")

def setup(bot):
    bot.add_cog(Roles(bot))
