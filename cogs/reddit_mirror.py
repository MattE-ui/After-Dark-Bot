import discord
from discord.ext import commands, tasks
import asyncpraw
import os
import json
from dotenv import load_dotenv
from discord import app_commands, Interaction

load_dotenv()
CONFIG_PATH = "config.json"

def _load_config() -> dict:
    """
    Load the JSON config file. Assume defaults if missing.
    """
    defaults = {
        "welcome_enabled": False,
        "reddit_enabled": True,
        "reddit_channel_id": None
    }
    if not os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "w") as f:
            json.dump(defaults, f, indent=4)
        return defaults

    with open(CONFIG_PATH, "r") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            data = defaults

    # Fill in any missing keys
    for key, val in defaults.items():
        if key not in data:
            data[key] = val

    return data

class ImagePaginator(discord.ui.View):
    def __init__(self, base_embed: discord.Embed, image_urls: list, timeout: int = 120):
        super().__init__(timeout=timeout)
        self.base_embed = base_embed
        self.image_urls = image_urls
        self.current_index = 0
        self.total = len(image_urls)
        self.update_buttons()

    def update_buttons(self):
        # Disable prev if at first, next if at last
        self.prev_button.disabled = (self.current_index == 0)
        self.next_button.disabled = (self.current_index == self.total - 1)

    @discord.ui.button(label="◀️", style=discord.ButtonStyle.secondary, custom_id="prev_image")
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_index -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="▶️", style=discord.ButtonStyle.secondary, custom_id="next_image")
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_index += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    def build_embed(self) -> discord.Embed:
        embed = self.base_embed.copy()
        embed.set_image(url=self.image_urls[self.current_index])
        embed.set_footer(text=f"Page {self.current_index + 1}/{self.total} | " + embed.footer.text)
        return embed

class RedditMirror(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.reddit = asyncpraw.Reddit(
            client_id=os.getenv("REDDIT_CLIENT_ID"),
            client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
            username=os.getenv("REDDIT_USERNAME"),
            password=os.getenv("REDDIT_PASSWORD"),
            user_agent=os.getenv("REDDIT_USER_AGENT")
        )
        self.subreddit_name = os.getenv("REDDIT_SUBREDDIT", "duneawakening")
        self.posted_ids = set()

        # Start the auto‐loop
        self.mirror_posts.start()

    def cog_unload(self):
        self.mirror_posts.cancel()

    async def is_already_sent(self, channel: discord.TextChannel, title: str) -> bool:
        """
        Scan the last 200 messages in 'channel' for an embed with same title.
        Return True if found.
        """
        async for message in channel.history(limit=200):
            if message.embeds:
                for embed in message.embeds:
                    if embed.title == title:
                        return True
        return False

    def extract_image_urls(self, submission) -> list:
        """
        Collect all image URLs: gallery → preview → single‐image fallback.
        """
        urls = []

        # 1) gallery
        if getattr(submission, "is_gallery", False) and hasattr(submission, "media_metadata"):
            try:
                for item in submission.media_metadata.values():
                    if "s" in item and "u" in item["s"]:
                        urls.append(item["s"]["u"].replace("&amp;", "&"))
            except Exception:
                pass

        # 2) preview images
        elif getattr(submission, "preview", None):
            try:
                for image in submission.preview.get("images", []):
                    src = image.get("source", {})
                    if "url" in src:
                        urls.append(src["url"].replace("&amp;", "&"))
            except Exception:
                pass

        # 3) fallback if direct image
        elif getattr(submission, "post_hint", None) == "image" and submission.url.endswith((".jpg", ".jpeg", ".png", ".gif")):
            urls.append(submission.url)

        return urls

    async def send_embed_with_images(self, channel: discord.TextChannel, submission, interaction: Interaction = None):
        """
        Build+send an embed for 'submission'. If multiple images, attach a paginator.
        If 'interaction' is provided, respond/followup on it; otherwise do a plain send().
        """
        embed = discord.Embed(
            title=submission.title,
            url=f"https://reddit.com{submission.permalink}",
            description=(submission.selftext[:300] + "..." if submission.selftext else None),
            color=discord.Color.orange()
        )
        embed.set_author(name=f"r/{self.subreddit_name}")
        embed.set_footer(text=f"Posted by u/{submission.author} | 👍 {submission.score}")

        image_urls = self.extract_image_urls(submission)

        if image_urls:
            # If more than one image, use paginator
            if len(image_urls) > 1:
                embed.set_image(url=image_urls[0])
                view = ImagePaginator(embed, image_urls)
                if interaction:
                    # Defer + followup if invoked via slash
                    await interaction.response.defer()
                    await interaction.followup.send(embed=embed, view=view)
                else:
                    await channel.send(embed=embed, view=view)
            else:
                # Single image
                embed.set_image(url=image_urls[0])
                if interaction:
                    await interaction.response.send_message(embed=embed)
                else:
                    await channel.send(embed=embed)
        else:
            # No images at all
            if interaction:
                await interaction.response.send_message(embed=embed)
            else:
                await channel.send(embed=embed)

    @tasks.loop(minutes=2.0)
    async def mirror_posts(self):
        await self.bot.wait_until_ready()

        # Re‐load config on each loop
        config = _load_config()
        if not config.get("reddit_enabled", True):
            return  # Auto‐mirror disabled

        channel_id = config.get("reddit_channel_id")
        if not channel_id:
            # Destination not set; nothing to do
            return

        channel = self.bot.get_channel(int(channel_id))
        if not channel:
            print(f"❌ Could not find channel with ID {channel_id}")
            return

        subreddit = await self.reddit.subreddit(self.subreddit_name)

        async for submission in subreddit.new(limit=5):
            if submission.id in self.posted_ids:
                continue

            await submission.load()

            if submission.score < 30:
                continue

            if await self.is_already_sent(channel, submission.title):
                continue

            self.posted_ids.add(submission.id)
            await self.send_embed_with_images(channel, submission)

    @mirror_posts.before_loop
    async def before_mirror_posts(self):
        await self.bot.wait_until_ready()

    @app_commands.command(name="reddit_latest", description="Post the newest r/duneawakening entry (≥30 upvotes).")
    async def reddit_latest(self, interaction: Interaction):
        try:
            subreddit = await self.reddit.subreddit(self.subreddit_name)
            found_submission = None

            async for post in subreddit.new(limit=10):
                await post.load()
                if post.score >= 30:
                    found_submission = post
                    break

            if not found_submission:
                await interaction.response.send_message(
                    "⚠️ Could not find any recent post with at least 30 upvotes.",
                    ephemeral=False
                )
                return

            # **Important**: We do NOT check for duplicates here, so /reddit_latest always shows you latest.
            await self.send_embed_with_images(interaction.channel, found_submission, interaction=interaction)

        except Exception as e:
            # If “thinking” wasn’t sent yet, use response.send_message
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ An error occurred: `{e}`")
            else:
                await interaction.followup.send(f"❌ An error occurred: `{e}`")
            raise

    async def cog_load(self):
        guild_id = os.getenv("GUILD_ID")
        if guild_id:
            guild_obj = discord.Object(id=int(guild_id))
            # Register /reddit_latest if not already there
            if not any(cmd.name == "reddit_latest" for cmd in self.bot.tree.get_commands(guild=guild_obj)):
                self.bot.tree.add_command(self.reddit_latest, guild=guild_obj)

async def setup(bot):
    await bot.add_cog(RedditMirror(bot))
