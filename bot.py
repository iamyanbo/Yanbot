import os
import discord
from dotenv import load_dotenv 
from discord.ext import commands
import main_commands
cogs = [main_commands]

client = commands.Bot(command_prefix = '.')
@client.event
async def on_ready():
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name='The Boys .help'))
    print('Online')

for i in range(len(cogs)):
    cogs[i].setup(client)

load_dotenv()
token = os.getenv('DISCORD_TOKEN')
client.run(token)