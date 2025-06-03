import discord
from discord.ext import commands
from discord.utils import get
from discord import app_commands
import os

welcome_enabled = False  # toggle flag

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
        global welcome_enabled
        if not welcome_enabled:
            print(f"Welcome disabled. {member.display_name} joined.")
            return

        message = (
            f"🎉 Welcome to the server, {member.mention}!\n\n"
            "Please select your game of interest below to get the appropriate role:"
        )
        view = GameRoleSelection(member.id)
        try:
            await member.send(message, view=view)
        except discord.Forbidden:
            fallback_channel = get(member.guild.text_channels, name="﹐chat") or \
                               get(member.guild.text_channels, name="welcome") or \
                               member.guild.text_channels[0]
            if fallback_channel:
                await fallback_channel.send(message, view=view)

    #@app_commands.command(name="toggle_welcome", description="(Developer Only) Toggle welcome messages.")
    async def toggle_welcome(self, interaction: discord.Interaction):
        developer_id = os.getenv("DEVELOPER_ID")
        if not developer_id or str(interaction.user.id) != developer_id:
            await interaction.response.send_message("❌ This command is restricted to the bot developer.", ephemeral=True)
            return

        global welcome_enabled
        welcome_enabled = not welcome_enabled
        state = "enabled" if welcome_enabled else "disabled"
        await interaction.response.send_message(f"✅ Welcome messages are now **{state}**.", ephemeral=True)

    @app_commands.command(name="test_welcome", description="(Developer Only) Test welcome flow.")
    async def test_welcome(self, interaction: discord.Interaction):
        developer_id = os.getenv("DEVELOPER_ID")
        if not developer_id or str(interaction.user.id) != developer_id:
            await interaction.response.send_message("❌ This command is restricted to the bot developer.", ephemeral=True)
            return

        view = GameRoleSelection(interaction.user.id)
        await interaction.response.send_message(
            f"🎉 Welcome to the server, {interaction.user.mention}!\n\nSelect your game below:",
            view=view,
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(Welcome(bot))
