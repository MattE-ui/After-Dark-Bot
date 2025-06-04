# cogs/dune_news.py

import discord
from discord.ext import commands, tasks
from discord import app_commands
from bs4 import BeautifulSoup
import aiohttp
import sqlite3
from datetime import datetime
from database.config_store import get_config

DB_PATH = "dune_news.sqlite3"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/113.0 Safari/537.36"
    )
}
NEWS_INDEX = "https://duneawakening.com/news"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS posted_articles (
            url TEXT PRIMARY KEY,
            posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def has_been_posted(url):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT 1 FROM posted_articles WHERE url = ?", (url,))
    result = c.fetchone()
    conn.close()
    return result is not None


def mark_as_posted(url):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO posted_articles (url) VALUES (?)", (url,))
    conn.commit()
    conn.close()


async def fetch_html(session, url):
    try:
        async with session.get(url, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=10)) as res:
            if res.status != 200:
                return None, f"HTTP {res.status} error"
            return await res.text(), None
    except Exception as e:
        return None, str(e)


async def fetch_news_urls(session, limit=5):
    html, error = await fetch_html(session, NEWS_INDEX)
    if error or html is None:
        return [], error or "Failed to fetch news index."

    soup = BeautifulSoup(html, "html.parser")
    links = soup.find_all("a")

    seen = set()
    urls = []
    for a in links:
        href = a.get("href", "")
        if href.startswith("https://duneawakening.com/news/") and href not in seen:
            seen.add(href)
            urls.append(href)
        if len(urls) >= limit:
            break

    return urls, None if urls else "No articles found."


async def fetch_article_content(session, url):
    html, error = await fetch_html(session, url)
    if error or html is None:
        return "", "", "", None, error

    soup = BeautifulSoup(html, "html.parser")
    title = soup.find("h1").get_text(strip=True) if soup.find("h1") else "Untitled"

    # Get hero image from <meta property="og:image">
    image = None
    og_tag = soup.find("meta", property="og:image")
    if og_tag and og_tag.get("content", "").startswith("https://"):
        image = og_tag["content"].strip()

    # Extract content paragraphs
    body = (
        soup.find("div", class_="content")
        or soup.find("div", class_="brxe-text-basic news-archive__text")
        or soup.find("main")
    )
    paragraphs = [p.get_text(strip=True) for p in body.find_all("p")] if body else []
    content = "\n\n".join(paragraphs)

    published = None
    time_tag = soup.find("time")
    if time_tag and time_tag.has_attr("datetime"):
        try:
            published = datetime.fromisoformat(time_tag["datetime"].replace("Z", "+00:00"))
        except Exception:
            published = datetime.utcnow()

    return title, content, image, published, None


def trim_to_paragraph_limit(text, limit=1800):
    """Trim article at paragraph boundaries within a char limit."""
    result = ""
    total = 0
    for paragraph in text.split("\n\n"):
        if total + len(paragraph) + 2 > limit:
            break
        result += paragraph + "\n\n"
        total += len(paragraph) + 2
    return result.strip() + ("…" if total >= limit else "")


def summarize_by_word_limit(text, word_limit=100):
    """Build 100-word summary, keeping paragraph breaks."""
    paragraphs = text.split("\n\n")
    result = ""
    count = 0
    for p in paragraphs:
        words = p.split()
        if count + len(words) <= word_limit:
            result += p + "\n\n"
            count += len(words)
        else:
            remain = word_limit - count
            if remain > 0:
                result += " ".join(words[:remain]) + "…"
            break
    return result.strip()


class ReadMoreView(discord.ui.View):
    def __init__(self, url):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="📖 Read Full Article", url=url))


class DuneNews(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        init_db()
        self.auto_post_news.start()

    def cog_unload(self):
        self.auto_post_news.cancel()

    @tasks.loop(minutes=10)
    async def auto_post_news(self):
        await self.bot.wait_until_ready()
        channel_id = get_config("dune_news_channel_id")
        if not channel_id:
            return
        channel = self.bot.get_channel(channel_id)
        if not isinstance(channel, discord.TextChannel):
            return

        async with aiohttp.ClientSession() as session:
            urls, err = await fetch_news_urls(session, limit=5)
            if err or not urls:
                return

            for url in urls:
                if has_been_posted(url):
                    continue

                title, content, image, published, error = await fetch_article_content(session, url)
                if error or not content:
                    continue

                display_text = trim_to_paragraph_limit(content)

                embed = discord.Embed(
                    title=title,
                    description=display_text,
                    color=0xDEB887,
                    timestamp=published or discord.utils.utcnow(),
                    url=url
                )
                if image:
                    embed.set_image(url=image)
                embed.set_footer(text="Dune: Awakening News")

                await channel.send(embed=embed, view=ReadMoreView(url))
                mark_as_posted(url)
                break

    @auto_post_news.before_loop
    async def before_auto_post(self):
        await self.bot.wait_until_ready()

    @app_commands.command(name="dune_news", description="Get the latest Dune: Awakening newsletter.")
    async def dune_news(self, interaction: discord.Interaction):
        await interaction.response.defer()
        async with aiohttp.ClientSession() as session:
            urls, err = await fetch_news_urls(session)
            if err or not urls:
                return await interaction.followup.send(f"❌ {err or 'No news found.'}")

            for url in urls:
                title, content, image, published, error = await fetch_article_content(session, url)
                if error or not content:
                    continue

                display_text = trim_to_paragraph_limit(content)

                embed = discord.Embed(
                    title=title,
                    description=display_text,
                    color=0xDEB887,
                    timestamp=published or discord.utils.utcnow(),
                    url=url
                )
                if image:
                    embed.set_image(url=image)
                embed.set_footer(text="Dune: Awakening News")

                return await interaction.followup.send(embed=embed, view=ReadMoreView(url))

            await interaction.followup.send("❌ Could not fetch any valid news posts.")

    @app_commands.command(name="dune_news_summary", description="Summarize the last 3 Dune: Awakening posts.")
    async def dune_news_summary(self, interaction: discord.Interaction):
        await interaction.response.defer()
        async with aiohttp.ClientSession() as session:
            urls, err = await fetch_news_urls(session)
            if err or not urls:
                return await interaction.followup.send(f"❌ {err or 'No news found.'}")

            sent = 0
            for url in urls:
                title, content, image, published, error = await fetch_article_content(session, url)
                if error or not content:
                    continue

                summary = summarize_by_word_limit(content)

                embed = discord.Embed(
                    title=title,
                    description=summary,
                    color=discord.Color.dark_gold(),
                    timestamp=published or discord.utils.utcnow(),
                    url=url
                )
                if image:
                    embed.set_image(url=image)
                embed.set_footer(text="Dune: Awakening News")

                await interaction.followup.send(embed=embed, view=ReadMoreView(url))
                sent += 1
                if sent >= 3:
                    break

            if sent == 0:
                await interaction.followup.send("❌ No valid summaries found.")


async def setup(bot):
    await bot.add_cog(DuneNews(bot))
