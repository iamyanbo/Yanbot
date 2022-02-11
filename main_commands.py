import time
import discord
from discord.ext import commands
import asyncio
import util

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
    
    @commands.command(name='help', aliases = ['h'])
    async def help(self, ctx):
        await ctx.channel.send('```I am Yanbot, a Discord bot made by Yanbo.\n')
        
    @commands.command(name = 'disconnect', aliases = ['dc'])
    async def disconnect(self, ctx):
        vc = ctx.author.voice.channel if ctx.author.voice is not None else None
        if vc is None:
            await ctx.channel.send('I am not in a voice channel.')
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
            self.playlist_ty.append('https://youtu.be/{}'.format(results[0]['id']))
        if len(self.playlist_yt) > 1:
            await ctx.send('{} songs added to the playlist.'.format(len(self.playlist_yt)))
        elif len(self.playlist_yt) == 1:
            await ctx.send('Queued {}.'.format(self.playlist_yt[0]))
        else:
            return await ctx.send('No songs added to the queue.')
        #check if player is playing
        if player.is_playing():
            return await ctx.send('Already playing.')
        else:
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
        if self.connect_vc(ctx) is False:
            return await ctx.send('You are not in a voice channel.')
        player = self.players[ctx.guild.id]
        if player.is_playing():
            player.stop()
            self.skip_next_callback = True
            await ctx.send('Stopped.')
            
    @commands.command(name = 'skip')
    async def skip(self, ctx):
        if self.connect_vc(ctx) is False:
            return await ctx.send('You are not in a voice channel.')
        player = self.players[ctx.guild.id]
        if 0 >= len(self.playlist_yt):
            await ctx.send('End of queue.')
        else:
            self.playlist_google.pop(0)
            self.playlist_yt.pop(0)
            player.play(self.playlist[0])
            
    @commands.command(name = 'queue', aliases = ['q'])
    async def queue(self, ctx):
        await ctx.channel.send('Currently Queued:\n')
        try:
            await ctx.channel.send('\n'.join(self.playlist_yt))
        except:
            await ctx.channel.send('None.')
    
    @commands.command(name = 'skip', aliases = ['s'])
    async def skip(self, ctx):
        if await self.connect_vc(ctx):
            if len(self.playlist_yt) <= 1:
                self.playlist_google.pop(0)
                self.playlist_yt.pop(0)
                self.players[ctx.guild.id].stop()
            else:
                await self.play_next(ctx)
        else:
            await ctx.channel.send('You are not in a voice channel.')
    
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

    @commands.command(name = 'revive', aliases = ['r'])
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
def setup(client):
    client.add_cog(main_commands(client))
    
