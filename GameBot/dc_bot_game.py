import discord
from discord.ext import commands, tasks
import aiohttp
import asyncio

# --- CONFIGURATION ---
TOKEN = 'MTQ5MDI0ODgyNDIzOTgyMDkyMA.G1FOWF.2RCXqEL084FNlH98XjPh3dPipUTaR81MX31KfY'  # RESET THIS IN DEV PORTAL IMMEDIATELY!
CHANNEL_ID = 1471915660488478877  
# ---------------------

intents = discord.Intents.default()
intents.message_content = True

class GameBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.check_free_games.start()
        print("Background task started!")

    @tasks.loop(hours=24)
    async def check_free_games(self):
        await self.wait_until_ready()
        channel = self.get_channel(CHANNEL_ID)
        
        if not channel:
            print(f"Error: Could not find channel with ID {CHANNEL_ID}")
            return

        print("Checking for 100% free-to-keep games...")
        
        # Added type=game to filter out loot/skins
        api_url = "https://www.gamerpower.com/api/giveaways?type=game"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        found_any = False
                        
                        for game in data:
                            # REFINED FILTER:
                            # 1. Must be on your preferred platforms
                            # 2. Must be 'Active' (not expired)
                            # 3. Must NOT be 'N/A' (filters out permanently free-to-play games)
                            platforms = ["PC", "Steam", "Epic Games Store"]
                            is_platform = any(p in game['platforms'] for p in platforms)
                            
                            if is_platform and game['status'] == 'Active' and game['worth'] != "N/A":
                                found_any = True
                                
                                embed = discord.Embed(
                                    title=f"FREE: {game['title']}",
                                    description=game['description'],
                                    color=discord.Color.green(), # Green for freebies
                                    url=game['open_giveaway_url']
                                )
                                embed.set_image(url=game['image'])
                                embed.add_field(name="Platform", value=game['platforms'], inline=True)
                                embed.add_field(name="Original Value", value=game['worth'], inline=True)
                                embed.set_footer(text="Grab it before the deal ends!")
                                
                                await channel.send(embed=embed)
                                await asyncio.sleep(1) 
                        
                        if not found_any:
                            print("No new paid games are currently 100% off.")
                    else:
                        print(f"API Error: {response.status}")
        except Exception as e:
            print(f"An error occurred: {e}")

bot = GameBot()

@bot.event
async def on_ready():
    print(f'--- Bot is Online ---')
    print(f'Logged in as: {bot.user.name}')
    print('----------------------')

bot.run(TOKEN)