from asyncore import loop
from threading import Timer
import time
from urllib.error import HTTPError
import discord
from discord.ext import commands, tasks
import asyncio
import util
import requests
import json

class main_commands(commands.Cog):
    def __init__(self, client) -> None:
        super().__init__()
        self.client = client
        self.client.remove_command('help')
        self.players = {}
        #if i want to make the bot be able to join multiple servers
        #i would make this into a dictionary with the server id as the key
        self.playlist_yt = []
        self.playlist_google = []
        self.bazaar.start()
        self.delete_items.start()
        self.items = []

    @commands.Cog.listener()
    async def on_ready(self):
        await self.client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name='The Boys .help'))
        print('Bot is ready.')   
        
    @commands.command(name='help', aliases = ['h'])
    async def help(self, ctx):
        await ctx.channel.send('```I am Yanbot, a Discord bot made by Yanbo.\n```')
        
    @commands.command(name = 'disconnect', aliases = ['dc'])
    async def disconnect(self, ctx):
        vc = ctx.author.voice.channel if ctx.author.voice is not None else None
        if vc is None:
            await ctx.channel.send('You are not in a voice channel.')
            return
        await ctx.voice_client.disconnect()
        del self.players[ctx.guild.id]
        
    async def connect_vc(self, ctx) -> bool:
        vc = ctx.author.voice.channel if ctx.author.voice is not None else None
        if vc is None:
            return False
        if ctx.voice_client is not None and ctx.voice_client.is_connected():
            await ctx.voice_client.move_to(vc)
        else:
            voice_client = await vc.connect()
            self.players[ctx.guild.id] = voice_client
        return True
    
    async def play_next(self, ctx):
        if 0 >= len(self.playlist_yt):
            return False
        else:
            self.playlist_google.pop(0)
            self.playlist_yt.pop(0)
        return await self.play_song(ctx)
    
    async def play_song(self, ctx):
        try:
            url = self.playlist_google[0]
            await ctx.channel.send(f'Now playing: {self.playlist_yt[0]}')
            FFMPEG_OPTIONS = {'before_options':'-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                                                            'options': '-vn'}
            source = await discord.FFmpegOpusAudio.from_probe(url, **FFMPEG_OPTIONS)
            self.skip_next_callback = True
            if self.players[ctx.guild.id].is_playing():
                self.players[ctx.guild.id].stop()
            loop = asyncio.get_running_loop()

            def handle_next(error):
                if self.skip_next_callback:
                    self.skip_next_callback = False
                    return
                asyncio.run_coroutine_threadsafe(self.play_next(ctx), loop)
            vc = self.players[ctx.guild.id]
            vc.play(source, after=handle_next)
            await asyncio.sleep(1)
            self.skip_next_callback = False
        except HTTPError as err:
            if err.code == 403:
                await ctx.channel.send('The song you requested is not available.')
                await self.play_next(ctx)

    @commands.command(name = 'play', aliases = ['p'])
    async def play(self, ctx, *message):
        message = ' '.join(message)
        if message is None or message.strip() == '':
            return await ctx.send('Please enter a URL or name.')
        if await self.connect_vc(ctx) is False:
            return await ctx.send('You are not in a voice channel.')
        player = self.players[ctx.guild.id]
        if util.is_url(message):
            #check if url is valid or not
            if '&list=' in message:
                await ctx.channel.send('Requesting playlist, please wait...')
                info = await util.youtube_extract_info(message, playlist = True)
                for ele in info['entries']:
                    self.playlist_google.append(ele['url'])
                    self.playlist_yt.append('https://youtu.be/{}'.format(ele['id']))
            elif 'youtu.be' in message or '/watch?v=' in message:
                info = await util.youtube_extract_info(message)
                self.playlist_yt.append('https://youtu.be/{}'.format(info['id']))
                self.playlist_google.append(info['url'])
        else:
            search = await util.youtube_extract_info(message)
            results = list(search['entries'])
            url = results[0]['url']
            self.playlist_google.append(url)
            self.playlist_yt.append('https://youtu.be/{}'.format(results[0]['id']))
        if len(self.playlist_yt) > 1:
            await ctx.send('{} songs added to the playlist.'.format(len(self.playlist_yt)))
        elif len(self.playlist_yt) == 1:
            msg = await ctx.send('Queued {}.'.format(self.playlist_yt[0]))
            await msg.edit(embed = None)
        else:
            return await ctx.send('No songs added to the queue.')
        #check if player is playing
        if not player.is_playing():
            await self.play_song(ctx)
        
    @commands.command(name = 'pause')
    async def pause(self, ctx):
        if await self.connect_vc(ctx) is False:
            return await ctx.send('You are not in a voice channel.')
        player = self.players[ctx.guild.id]
        if player.is_playing():
            player.pause()
            await ctx.send('Paused.')
        else:
            await ctx.send('Nothing is playing.')
    
    @commands.command(name = 'resume')
    async def resume(self, ctx):
        if await self.connect_vc(ctx) is False:
            return await ctx.send('You are not in a voice channel.')
        player = self.players[ctx.guild.id]
        if player.is_paused():
            player.resume()
            await ctx.send('Resumed.')
        else:
            await ctx.send('Nothing is paused.')
    
    @commands.command(name = 'stop')
    async def stop(self, ctx):
        if await self.connect_vc(ctx) is False:
            return await ctx.send('You are not in a voice channel.')
        player = self.players[ctx.guild.id]
        if player.is_playing():
            player.stop()
            self.skip_next_callback = True
            await ctx.send('Stopped.')
        else:
            await ctx.send('Nothing is playing.')
            
    @commands.command(name = 'skip', aliases = ['s'])
    async def skip(self, ctx):
        if await self.connect_vc(ctx) is False:
            return await ctx.send('You are not in a voice channel.')
        else:
            if 0 == len(self.playlist_yt):
                return await ctx.send('End of queue.')
            elif len(self.playlist_yt) == 1:
                    self.playlist_google.pop(0)
                    self.playlist_yt.pop(0)
                    self.players[ctx.guild.id].stop()
            else:
                await self.play_next(ctx)
            
    @commands.command(name = 'queue', aliases = ['q'])
    async def queue(self, ctx):
        await ctx.channel.send('Currently Queued:\n')
        try:
            await ctx.channel.send('\n'.join(self.playlist_yt))
        except:
            await ctx.channel.send('None.')
            
    @commands.command()
    async def wheres(self, ctx, message):
        if message == '<@!361913675872731136>':
            user = '<@!361913675872731136>'
            await ctx.channel.send(f'{user} downstairs showering with his bri\'ish cousins playing csgo and eating and taking a LGBTQ poop')
        if message == '<@432949846991831040>':
            user = '<@432949846991831040>'
            await ctx.channel.send(f'{user} is ganked 😂🤣😔😴💀')
        if message == '<@!516624806515572737>':
            user = '<@!516624806515572737>'
            await ctx.channel.send(f'{user} is buying stone swords again... 😭🤢🤢🤢😰')
        if message == '<@207568895156944896>':
            user = '<@207568895156944896>'
            await ctx.channel.send(f'{user} is being the better brother and probs doing nothing rn cus he is lazy')
        if message == '<@!194955178770825216>':
            user = '<@!194955178770825216>'
            await ctx.channel.send(f'{user} is being sus and needs to be paused')

    @commands.command(name = 'revive')
    async def revive(self, ctx, member: discord.Member):
        try:
            voice_channel = ctx.guild.voice_channels
            await member.move_to(voice_channel[1])
            time.sleep(0.5)
            await member.move_to(voice_channel[0])
            time.sleep(0.5)
            await member.move_to(voice_channel[1])
            time.sleep(0.5)
            await member.move_to(voice_channel[0])
            time.sleep(0.5)
            await member.move_to(voice_channel[1])
            time.sleep(0.5)
            await member.move_to(voice_channel[0])
            time.sleep(0.5)
            await member.move_to(voice_channel[1])
            time.sleep(0.5)
            await member.move_to(voice_channel[0])
        except:
            await ctx.channel.send('person not in vc')
            
    
            
    @tasks.loop(seconds = 10)
    async def bazaar(self):
    #fetch data from hypixel skyblock bazaar api
        response = requests.get('https://api.hypixel.net/skyblock/bazaar?key=065f77c0-ef85-44e9-8303-aa8e3dd6a81b').json()
        channel = self.client.get_channel(207569089059618816)
        for ele in response['products']:
            try:
                if ele not in self.items:
                    quick_sell = response['products'][ele]['quick_status']['sellPrice']
                    quick_buy = response['products'][ele]['quick_status']['buyPrice']
                    lowest_sell = response['products'][ele]['sell_summary'][0]['pricePerUnit']
                    lowest_buy = response['products'][ele]['buy_summary'][0]['pricePerUnit']
                    sell_volume = response['products'][ele]['quick_status']['sellVolume']
                    buy_volume = response['products'][ele]['quick_status']['buyVolume']
                    if lowest_buy / lowest_sell > 2:
                        if sell_volume > 200000 and buy_volume > 200000:
                            if quick_buy > 700:
                                if quick_sell / lowest_sell > 2:
                                    await channel.send(f'{ele} price is below average with \n{lowest_sell} sell \n{lowest_buy} buy \n{quick_sell} 7 day quick sell \n{quick_buy} 7 day quick buy\n')
                                    self.items.append(ele)
                                elif lowest_buy / quick_buy > 2:
                                    await channel.send(f'{ele} price is above average with \n{lowest_sell} sell \n{lowest_buy} buy \n{quick_sell} 7 day quick sell \n{quick_buy} 7 day quick buy\n')
                                    self.items.append(ele)
                                else:
                                    await channel.send(f'{ele} is a great flip with \n{lowest_sell} sell \n{lowest_buy} buy \n{quick_sell} 7 day quick sell \n{quick_buy} 7 day quick buy\n')
                                    self.items.append(ele)     
                    elif lowest_buy / lowest_sell > 1.1:
                        if sell_volume > 200000 and buy_volume > 200000:
                            if quick_buy > 700:
                                await channel.send(f'{ele} is a good flip with \n{lowest_sell} sell \n{lowest_buy} buy \n{quick_sell} 7 day quick sell \n{quick_buy} 7day quick buy\n')
                                self.items.append(ele)
            except:
                continue
        
    @tasks.loop(seconds = 3600)
    async def delete_items(self):
        self.items.clear()
        
def setup(client):
    client.add_cog(main_commands(client))
    
