import discord
from discord.ext import commands
from discord.utils import get
from discord import app_commands
import os
from cogs.config_store import get_setting, set_setting

class GameRoleSelection(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=300)
        self.user_id = user_id

    async def disable_all(self, interaction):
        for item in self.children:
            item.disabled = True
        await interaction.edit_original_response(view=self)

    @discord.ui.button(label="🏜️ Dune: Awakening", style=discord.ButtonStyle.primary)
    async def dune_button(self, button, interaction):
        await self.assign_role(interaction, "Fremen")

    @discord.ui.button(label="🔫 Division 2", style=discord.ButtonStyle.secondary)
    async def division_button(self, button, interaction):
        await self.assign_role(interaction, "SHD Agent")

    @discord.ui.button(label="❓ Neither/Other", style=discord.ButtonStyle.danger)
    async def neither_button(self, button, interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This button is not for you!", ephemeral=True)
            return
        await interaction.response.send_message(
            "No problem! You can contact an admin if you need a specific game role later.",
            ephemeral=True
        )
        await self.disable_all(interaction)

    async def assign_role(self, interaction, role_name):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This button is not for you!", ephemeral=True)
            return

        member = interaction.guild.get_member(interaction.user.id)
        role = get(interaction.guild.roles, name=role_name)

        if role and member:
            await member.add_roles(role)
            await interaction.response.send_message(f"✅ You've been given the **{role.name}** role!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Role not found or user not in guild.", ephemeral=True)

        await self.disable_all(interaction)

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        # Check if welcome is enabled in settings
        welcome_enabled = bool(int(get_setting("welcome_enabled", 0)))
        if not welcome_enabled:
            print(f"Welcome is disabled. Skipping DM to {member.display_name}.")
            return

        message = (
            f"🎉 Welcome to the server, {member.mention}!\n\n"
            "Please select your game of interest below to get the appropriate role:"
        )
        view = GameRoleSelection(member.id)
        try:
            await member.send(message, view=view)
        except discord.Forbidden:
            fallback = (
                get(member.guild.text_channels, name="﹐chat") or
                get(member.guild.text_channels, name="welcome") or
                member.guild.text_channels[0]
            )
            if fallback:
                await fallback.send(message, view=view)

    @app_commands.command(
        name="toggle_welcome",
        description="(Developer Only) Enable or disable welcome DMs."
    )
    async def toggle_welcome(self, interaction: discord.Interaction):
        developer_id = os.getenv("DEVELOPER_ID")
        if not developer_id or str(interaction.user.id) != developer_id:
            await interaction.response.send_message("❌ Developer only.", ephemeral=True)
            return

        current = bool(int(get_setting("welcome_enabled", 0)))
        new_val = int(not current)
        set_setting("welcome_enabled", new_val)
        state = "enabled" if not current else "disabled"
        await interaction.response.send_message(f"✅ Welcome messages are now **{state}**.", ephemeral=True)

    @app_commands.command(
        name="test_welcome",
        description="(Developer Only) Test the welcome DM flow."
    )
    async def test_welcome(self, interaction: discord.Interaction):
        developer_id = os.getenv("DEVELOPER_ID")
        if not developer_id or str(interaction.user.id) != developer_id:
            await interaction.response.send_message("❌ Developer only.", ephemeral=True)
            return

        view = GameRoleSelection(interaction.user.id)
        await interaction.response.send_message(
            f"🎉 Welcome to the server, {interaction.user.mention}!\n\nSelect your game below:",
            view=view,
            ephemeral=True
        )

    async def cog_load(self):
        """
        Ensure toggle_welcome & test_welcome are registered to the guild only once.
        """
        guild_id = os.getenv("GUILD_ID")
        if guild_id:
            guild_obj = discord.Object(id=int(guild_id))
            names = [cmd.name for cmd in self.bot.tree.get_commands(guild=guild_obj)]
            if "toggle_welcome" not in names:
                self.bot.tree.add_command(self.toggle_welcome, guild=guild_obj)
            if "test_welcome" not in names:
                self.bot.tree.add_command(self.test_welcome, guild=guild_obj)

async def setup(bot: commands.Bot):
    await bot.add_cog(Welcome(bot))
