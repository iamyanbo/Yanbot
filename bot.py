import asyncio
import os
import discord
from dotenv import load_dotenv 
from discord.ext import commands
from discord import Intents

intents= Intents.all()
client = commands.Bot(command_prefix=".", intents=intents)

async def load():
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            await client.load_extension(f'cogs.{filename[:-3]}')
            
async def main():
    await load()
    load_dotenv()
    token = os.getenv('DISCORD_TOKEN')
    await client.start(token)

asyncio.run(main())