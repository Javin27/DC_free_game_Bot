import discord
from discord.ext import commands, tasks
import aiohttp
import asyncio
import json
import os
from dotenv import load_dotenv

load_dotenv()  # loads variables from a local .env file

token = os.getenv('DISCORD_TOKEN')  # <-- set DISCORD_TOKEN in your .env file

CONFIG_FILE = "guild_configs.json"
# ---------------------

intents = discord.Intents.default()
intents.message_content = True


def load_configs():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}


def save_configs(configs):
    with open(CONFIG_FILE, "w") as f:
        json.dump(configs, f, indent=2)


class GameBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        self.guild_configs = load_configs()  # {str(guild_id): channel_id}

    async def setup_hook(self):
        self.check_free_games.start()
        print("Background task started!")

    @tasks.loop(hours=24)
    async def check_free_games(self):
        await self.wait_until_ready()

        if not self.guild_configs:
            print("No servers have set up an announcement channel yet.")
            return

        print("Checking for 100% free-to-keep games...")

        api_url = "https://www.gamerpower.com/api/giveaways?type=game"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url) as response:
                    if response.status != 200:
                        print(f"API Error: {response.status}")
                        return

                    data = await response.json()
                    matching_games = []

                    for game in data:
                        platforms = ["PC", "Steam", "Epic Games Store"]
                        is_platform = any(p in game['platforms'] for p in platforms)

                        if is_platform and game['status'] == 'Active' and game['worth'] != "N/A":
                            matching_games.append(game)

                    if not matching_games:
                        print("No new paid games are currently 100% off.")
                        return

                    # Post each matching game to every configured server's channel
                    for guild_id, channel_id in list(self.guild_configs.items()):
                        channel = self.get_channel(channel_id)

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

        except Exception as e:
            print(f"An error occurred: {e}")


bot = GameBot()


@bot.event
async def on_ready():
    print(f'--- Bot is Online ---')
    print(f'Logged in as: {bot.user.name}')
    print(f'Active in {len(bot.guilds)} server(s)')
    print('----------------------')


@bot.event
async def on_guild_join(guild):
    """Greet the server when the bot is invited, and explain setup."""
    target = guild.system_channel
    if target is None:
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                target = channel
                break

    if target:
        await target.send(
            "👋 Thanks for adding **Free Games Bot**!\n"
            "An admin needs to run `!setchannel` in the channel where you want "
            "free game announcements posted."
        )


@bot.command()
@commands.has_permissions(administrator=True)
async def setchannel(ctx):
    """Set the current channel as this server's free-games announcement channel."""
    bot.guild_configs[str(ctx.guild.id)] = ctx.channel.id
    save_configs(bot.guild_configs)
    await ctx.send(f"✅ Free game announcements will now be posted in {ctx.channel.mention}!")


@bot.command()
async def freegameschannel(ctx):
    """Show which channel is currently configured for this server."""
    channel_id = bot.guild_configs.get(str(ctx.guild.id))
    if channel_id:
        channel = bot.get_channel(channel_id)
        await ctx.send(f"Announcements are currently posted in {channel.mention if channel else channel_id}.")
    else:
        await ctx.send("No channel set yet! An admin can run `!setchannel` here to set one up.")


if __name__ == "__main__":
    if not token:
        raise SystemExit(
            "No token found! Create a .env file with a line like:\n"
            "DISCORD_TOKEN=your_actual_token_here"
        )
    bot.run(token)
