import os
import discord
from dotenv import load_dotenv 
from discord.ext import commands
import main_commands
cogs = [main_commands]

client = commands.Bot(command_prefix = '.')

for i in range(len(cogs)):
    cogs[i].setup(client)

load_dotenv()
token = os.getenv('DISCORD_TOKEN')
client.run(token)