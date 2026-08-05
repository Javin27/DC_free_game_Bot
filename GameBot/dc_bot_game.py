
import discord
import aiohttp
import asyncio
import json
import os
import sys
from datetime import datetime

token = os.getenv("DISCORD_TOKEN")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "guild_configs.json")


def load_configs():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)

    return {}


async def get_matching_games():
    """Fetch active free games and filter to Steam, Epic Games Store, and Itch.io only."""

    api_url = "https://www.gamerpower.com/api/giveaways?type=game"
    matching_games = []

    allowed_platforms = [
        "steam",
        "epic games store",
        "itch.io"
    ]

    async with aiohttp.ClientSession() as session:
        async with session.get(api_url) as response:

            if response.status != 200:
                print(f"API Error: {response.status}")
                return matching_games

            data = await response.json()

            for game in data:
                game_platforms = game.get("platforms", "").lower()

                is_allowed_platform = any(
                    platform in game_platforms
                    for platform in allowed_platforms
                )

                if (
                    is_allowed_platform
                    and game.get("status") == "Active"
                    and game.get("worth") != "N/A"
                ):
                    matching_games.append(game)

    return matching_games


async def main():

    if not token:
        print(
            "No token found! Set DISCORD_TOKEN as a repo secret "
            "or in your .env file."
        )
        sys.exit(1)

    guild_configs = load_configs()

    if not guild_configs:
        print(
            "No servers have a channel configured in "
            "guild_configs.json. Nothing to do."
        )
        return

    matching_games = await get_matching_games()

    if not matching_games:
        print("No matching free games found today. Nothing to post.")
        return

    intents = discord.Intents.default()
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():

        print(
            f"Logged in as {client.user}. "
            f"Posting to {len(guild_configs)} server(s)..."
        )

        # Current date
        current_date = datetime.now().strftime("%d %B %Y")

        for guild_id, channel_id in guild_configs.items():

            channel = client.get_channel(int(channel_id))

            if not channel:
                print(
                    f"Could not find channel {channel_id} "
                    f"for guild {guild_id}, skipping."
                )
                continue

            # Daily date header
            date_embed = discord.Embed(
                title="🎁 TODAY'S FREE GAMES",
                description=f"📅 **{current_date}**",
                color=discord.Color.blurple()
            )

            date_embed.set_footer(
                text="Free games available today"
            )

            await channel.send(embed=date_embed)

            # Send games
            for game in matching_games:

                embed = discord.Embed(
                    title=f"🎮 FREE: {game['title']}",
                    description=game.get(
                        "description",
                        "No description available."
                    ),
                    color=discord.Color.green(),
                    url=game["open_giveaway_url"]
                )

                if game.get("image"):
                    embed.set_image(url=game["image"])

                embed.add_field(
                    name="🎮 Platform",
                    value=game.get("platforms", "Unknown"),
                    inline=True
                )

                embed.add_field(
                    name="💰 Original Value",
                    value=game.get("worth", "N/A"),
                    inline=True
                )

                embed.set_footer(
                    text="Grab it before the deal ends!"
                )

                await channel.send(embed=embed)

                await asyncio.sleep(1)

        print("Done posting. Shutting down cleanly.")

        await client.close()


    await client.start(token)


if __name__ == "__main__":
    asyncio.run(main())
```
