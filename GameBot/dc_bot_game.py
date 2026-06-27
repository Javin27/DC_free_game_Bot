import discord
import aiohttp
import asyncio
import json
import os
import sys


  # only matters when running locally; on Actions, the secret is already an env var

token = os.getenv('DISCORD_TOKEN')

CONFIG_FILE = "guild_configs.json"


def load_configs():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}


async def get_matching_games():
    """Fetch free games from the API and filter to 100%-off PC games."""
    api_url = "https://www.gamerpower.com/api/giveaways?type=game"
    matching_games = []

    async with aiohttp.ClientSession() as session:
        async with session.get(api_url) as response:
            if response.status != 200:
                print(f"API Error: {response.status}")
                return matching_games

            data = await response.json()
            platforms = ["PC", "Steam", "Epic Games Store"]

            for game in data:
                is_platform = any(p in game['platforms'] for p in platforms)
                if is_platform and game['status'] == 'Active' and game['worth'] != "N/A":
                    matching_games.append(game)

    return matching_games


async def main():
    if not token:
        print("No token found! Set DISCORD_TOKEN as a repo secret or in your .env file.")
        sys.exit(1)

    guild_configs = load_configs()

    if not guild_configs:
        print("No servers have a channel configured in guild_configs.json. Nothing to do.")
        return

    matching_games = await get_matching_games()

    if not matching_games:
        print("No 100%-off games found today. Nothing to post.")
        return

    intents = discord.Intents.default()
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print(f"Logged in as {client.user}. Posting to {len(guild_configs)} server(s)...")

        for guild_id, channel_id in guild_configs.items():
            channel = client.get_channel(channel_id)

            if not channel:
                print(f"Could not find channel {channel_id} for guild {guild_id}, skipping.")
                continue

            for game in matching_games:
                embed = discord.Embed(
                    title=f"FREE: {game['title']}",
                    description=game['description'],
                    color=discord.Color.green(),
                    url=game['open_giveaway_url']
                )
                embed.set_image(url=game['image'])
                embed.add_field(name="Platform", value=game['platforms'], inline=True)
                embed.add_field(name="Original Value", value=game['worth'], inline=True)
                embed.set_footer(text="Grab it before the deal ends!")

                await channel.send(embed=embed)
                await asyncio.sleep(1)

        print("Done posting. Shutting down cleanly.")
        await client.close()  # this lets the script exit instead of hanging forever

    await client.start(token)


if __name__ == "__main__":
    asyncio.run(main())
