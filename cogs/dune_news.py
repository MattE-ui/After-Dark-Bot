import asyncio
from datetime import datetime
import re
import os

import discord
from discord import app_commands
from discord.ext import commands
import requests
from bs4 import BeautifulSoup, NavigableString

# Re‐use our existing ReadMoreView from before (same as original)
class ReadMoreView(discord.ui.View):
    def __init__(self, url: str):
        super().__init__(timeout=None)
        self.add_item(
            discord.ui.Button(label="Read More", style=discord.ButtonStyle.link, url=url, emoji="📖")
        )

class News(commands.Cog):
    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        " AppleWebKit/537.36 (KHTML, like Gecko)"
        " Chrome/124.0.0.0 Safari/537.36"
    )

    NOISE_TERMS = {
        "home", "game", "news", "media", "wishlist",
        "pre-order", "beta signup", "share", "link copied",
    }

    BANNED_LINES = {
        "home", "game", "betasignup", "wishlistonsteam", "preordernow",
        "alldunegames", "wishlist", "preorder", "media", "news", "share",
        "linkcopied", "englishfrançaisespañoldeutsch中文", "pre-ordernow"
    }

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def fetch_dune_news(self):
        url = "https://www.duneawakening.com/en/news"
        headers = {"User-Agent": self.USER_AGENT}

        try:
            # Run requests.get in executor to avoid blocking
            response = await asyncio.get_event_loop().run_in_executor(
                None, lambda: requests.get(url, headers=headers, timeout=10)
            )
        except requests.RequestException as e:
            return None, f"Network error: {e!s}"

        if response.status_code != 200:
            return None, f"Failed to fetch news (status {response.status_code})"

        soup = BeautifulSoup(response.text, "html.parser")

        # Try multiple known selectors, fallback if none match
        selectors = [
            "a.article-card_link__XGiVr",
            ".article-card a",
            ".news-item a",
            "article a[href*='/en/news/']",
        ]
        for sel in selectors:
            articles = soup.select(sel)
            if articles:
                return articles, None

        # Fallback: brute‐force scan for <a> with '/en/news/'
        articles = [
            a for a in soup.find_all("a", href=True)
            if "/en/news/" in a["href"] and len(a.get_text(strip=True)) > 10
        ]
        if not articles:
            return None, "No news articles found."

        return articles, None

    async def fetch_article_content(self, url: str):
        headers = {"User-Agent": self.USER_AGENT}

        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None, lambda: requests.get(url, headers=headers, timeout=15)
            )
        except Exception as e:
            return None, None, None, None, f"Network error: {e}"

        if response.status_code != 200:
            return None, None, None, None, f"Failed to fetch article (status {response.status_code})"

        soup = BeautifulSoup(response.text, "html.parser")

        # Extract title
        title = soup.find("h1").get_text(strip=True) if soup.find("h1") else "News Update"

        # Extract publish date (if available in <time datetime="">)
        publish_date = datetime.utcnow()
        date_tag = soup.find("time")
        if date_tag and date_tag.has_attr("datetime"):
            try:
                publish_date = datetime.fromisoformat(date_tag["datetime"].replace("Z", "+00:00"))
            except Exception:
                pass

        # Extract og:image (if present)
        image_meta = soup.find("meta", property="og:image")
        image_url = image_meta["content"] if image_meta else None

        # Parse the page’s <body> for paragraphs, headings, list items
        body = soup.find("body")
        if not body:
            return title, "Content not available.", image_url, publish_date, None

        lines = []
        for tag in body.find_all(["p", "li", "h2", "h3"], recursive=True):
            text = tag.get_text(separator=" ", strip=True)
            if not text:
                continue

            normalized = text.lower().replace(" ", "")
            if any(bad in normalized for bad in self.BANNED_LINES):
                continue

            if tag.name in {"h2", "h3"}:
                lines.append(f"**{text}**")
            elif tag.name == "li":
                lines.append(f"• {text}")
            else:
                lines.append(text)

            lines.append("")  # Blank line for spacing

        content = "\n".join(lines)
        content = re.sub(r"\n{3,}", "\n\n", content).strip()

        return title, content, image_url, publish_date, None

    @app_commands.command(name="dune_news", description="Get the latest Dune: Awakening headline in full.")
    async def dune_news_slash(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self._send_latest_article(interaction, is_slash=True)

    @app_commands.command(name="latest_dune_news", description="Alias for /dune_news.")
    async def latest_dune_news(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self._send_latest_article(interaction, is_slash=True)

    @app_commands.command(name="dune_news_summary", description="Summaries of the three most recent posts.")
    async def dune_news_summary(self, interaction: discord.Interaction):
        await interaction.response.defer()

        articles, error = await self.fetch_dune_news()
        if error or not articles:
            await interaction.followup.send(f"❌ {error or 'No articles found.'}")
            return

        # Send header embed
        header = discord.Embed(
            title="Dune: Awakening — Recent News",
            description=f"Here are the latest **{min(3, len(articles))}** posts:",
            color=0xC8860D,
            timestamp=datetime.utcnow(),
        )
        await interaction.followup.send(embed=header)

        # Loop through top 3 articles
        for idx, article in enumerate(articles[:3], start=1):
            href = article.get("href", "")
            url = f"https://www.duneawakening.com{href}" if href.startswith("/") else href

            title, content, img, published, err = await self.fetch_article_content(url)
            if err:
                continue

            summary = " ".join(content.split()[:90]) + "…"
            embed = discord.Embed(
                title=title,
                description=summary,
                color=0xC8860D,
                timestamp=published,
                url=url,
            )
            if img:
                embed.set_thumbnail(url=img)
            embed.set_footer(text=f"Summary {idx} of {len(articles)}")
            await interaction.followup.send(embed=embed, view=ReadMoreView(url))
            await asyncio.sleep(1.0)  # slight delay to avoid spamming

    @commands.command(name="dune_news")
    async def dune_news_text(self, ctx: commands.Context):
        await self._send_latest_article(ctx)

    async def _send_latest_article(self, ctx, *, is_slash: bool = False):
        send = ctx.followup.send if is_slash else ctx.send

        articles, error = await self.fetch_dune_news()
        if error or not articles:
            await send(f"❌ {error or 'No articles found.'}")
            return

        href = articles[0].get("href", "")
        url = f"https://www.duneawakening.com{href}" if href.startswith("/") else href

        title, content, img, published, err = await self.fetch_article_content(url)
        if err:
            await send(f"❌ {err}")
            return

        description = (content[:1800] + "…") if len(content) > 1800 else content
        embed = discord.Embed(
            title=title,
            description=description,
            color=0xDEB887,
            timestamp=published,
            url=url,
        )
        if img:
            embed.set_image(url=img)
        embed.set_footer(text="Dune: Awakening News")
        await send(embed=embed, view=ReadMoreView(url))

    # Removed the old broken cog_load; slash commands are auto‐registered via decorator.

async def setup(bot: commands.Bot):
    await bot.add_cog(News(bot))
