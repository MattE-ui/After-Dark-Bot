# cogs/reddit_mirror.py

import discord
from discord.ext import commands, tasks
import praw
import os
from dotenv import load_dotenv

from discord import app_commands
from database.config_store import get_config, set_config

load_dotenv()


class RedditGalleryView(discord.ui.View):
    def __init__(self, images: list[str], embed: discord.Embed, author_tag: str):
        super().__init__(timeout=60)
        self.images = images
        self.index = 0
        self.embed = embed
        self.author_tag = author_tag
        self.update_embed()

    def update_embed(self):
        self.embed.set_image(url=self.images[self.index])
        self.embed.set_footer(text=f"{self.author_tag} • Image {self.index + 1} of {len(self.images)}")

    @discord.ui.button(label="◀️ Prev", style=discord.ButtonStyle.secondary)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = (self.index - 1) % len(self.images)
        self.update_embed()
        await interaction.response.edit_message(embed=self.embed, view=self)

    @discord.ui.button(label="Next ▶️", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = (self.index + 1) % len(self.images)
        self.update_embed()
        await interaction.response.edit_message(embed=self.embed, view=self)


class RedditMirror(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.subreddit_name = os.getenv("REDDIT_SUBREDDIT")
        self.channel_id = int(os.getenv("REDDIT_CHANNEL_ID"))
        self.default_min_upvotes = 20

        try:
            self.reddit = praw.Reddit(
                client_id=os.getenv("REDDIT_CLIENT_ID"),
                client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
                username=os.getenv("REDDIT_USERNAME"),
                password=os.getenv("REDDIT_PASSWORD"),
                user_agent=os.getenv("REDDIT_USER_AGENT")
            )
        except Exception as e:
            print(f"[RedditMirror] PRAW initialization failed: {e}")
            self.reddit = None

        self.posted_ids = set()
        self.check_reddit.start()

    def cog_unload(self):
        self.check_reddit.cancel()

    def get_min_upvotes(self):
        return get_config("reddit_min_upvotes") or self.default_min_upvotes

    def extract_gallery_images(self, submission) -> list[str]:
        images = []
        if hasattr(submission, "media_metadata"):
            try:
                for item in submission.gallery_data["items"]:
                    media_id = item["media_id"]
                    meta = submission.media_metadata[media_id]
                    url = meta["s"]["u"].replace("&amp;", "&")
                    images.append(url)
            except Exception as e:
                print(f"[RedditMirror] Failed to parse gallery: {e}")
        return images

    def create_embed_from_submission(self, submission, image_override=None):
        title = submission.title
        url = submission.url
        post_url = f"https://reddit.com{submission.permalink}"

        embed = discord.Embed(
            title=title,
            url=post_url,
            color=discord.Color.orange()
        )
        embed.set_author(name=f"Reddit /r/{self.subreddit_name}")
        embed.set_footer(text=f"Posted by u/{submission.author}")

        if submission.selftext and len(submission.selftext) < 1024:
            embed.description = submission.selftext

        if image_override:
            embed.set_image(url=image_override)
        elif url.lower().endswith((".jpg", ".png", ".gif", ".jpeg", ".webp")):
            embed.set_image(url=url)

        return embed

    @tasks.loop(minutes=1.5)
    async def check_reddit(self):
        if not get_config("reddit_enabled"):
            return

        if self.reddit is None:
            return

        try:
            subreddit = self.reddit.subreddit(self.subreddit_name)
            submissions = list(subreddit.new(limit=5))
        except Exception as e:
            print(f"[RedditMirror] Failed to fetch subreddit posts: {e}")
            return

        channel = self.bot.get_channel(self.channel_id)
        if channel is None or not isinstance(channel, discord.TextChannel):
            return

        min_upvotes = self.get_min_upvotes()

        for submission in submissions:
            if submission.id in self.posted_ids:
                continue
            if submission.score < min_upvotes:
                continue

            self.posted_ids.add(submission.id)

            if getattr(submission, "is_gallery", False):
                images = self.extract_gallery_images(submission)
                if not images:
                    continue
                embed = self.create_embed_from_submission(submission, image_override=images[0])
                view = RedditGalleryView(images, embed, f"Posted by u/{submission.author}")
                try:
                    await channel.send(embed=embed, view=view)
                except Exception as e:
                    print(f"[RedditMirror] Failed to send gallery post {submission.id}: {e}")
            else:
                embed = self.create_embed_from_submission(submission)
                try:
                    await channel.send(embed=embed)
                except Exception as e:
                    print(f"[RedditMirror] Failed to send embed for {submission.id}: {e}")

    @check_reddit.before_loop
    async def before_check_reddit(self):
        await self.bot.wait_until_ready()

    @app_commands.command(name="reddit_latest", description="Post the latest Reddit post that meets the upvote threshold.")
    async def reddit_latest(self, interaction: discord.Interaction):
        await interaction.response.defer()

        if self.reddit is None:
            await interaction.followup.send("❌ Reddit API not initialized.")
            return

        subreddit = self.reddit.subreddit(self.subreddit_name)
        min_upvotes = self.get_min_upvotes()

        try:
            for submission in subreddit.new(limit=10):
                if submission.score < min_upvotes:
                    continue

                if getattr(submission, "is_gallery", False):
                    images = self.extract_gallery_images(submission)
                    if not images:
                        continue
                    embed = self.create_embed_from_submission(submission, image_override=images[0])
                    view = RedditGalleryView(images, embed, f"Posted by u/{submission.author}")
                    await interaction.followup.send(embed=embed, view=view)
                else:
                    embed = self.create_embed_from_submission(submission)
                    await interaction.followup.send(embed=embed)
                return

            await interaction.followup.send("❌ No recent posts meet the upvote threshold.")
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to fetch Reddit posts: {e}")


async def setup(bot):
    await bot.add_cog(RedditMirror(bot))
