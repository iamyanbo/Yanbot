from threading import Timer
import time
from urllib.error import HTTPError
import discord
from discord.ext import commands, tasks
import asyncio
import util
from selenium import webdriver
from bs4 import BeautifulSoup

class Main_commands(commands.Cog):
    def __init__(self, client) -> None:
        super().__init__()
        self.client = client
        self.client.remove_command('help')
        self.players = {}
        #if i want to make the bot be able to join multiple servers
        #i would make this into a dictionary with the server id as the key
        self.playlist_yt = []
        self.playlist_google = []
        self.watching_list = []
        self.channel_number = 1071237492663128124 # set this to the channel you want the bot to send the message to
        self.spiked_items = []
        self.spike_threshold = 2 # set this to the threshold for what multiplier you consider a spike
        self.reasonable_buy_volume = 100 # set this to the threshold for what volume you consider a reasonable buy
        self.reasonable_sell_volume = 100 # set this to the threshold for what volume you consider a reasonable sell
        self.data = []

    @commands.command(name='rem')
    async def rem(self, ctx, *args):
        self.watching_list = list(args)
        await ctx.send("List updated.")
        
    @commands.command(name='add')
    async def add(self, ctx, *args):
        self.watching_list.extend(list(args))
        await ctx.send("List updated.")
        
    @commands.command(name='print')
    async def print(self, ctx):
        await ctx.send(self.watching_list)
        
    @commands.Cog.listener()
    async def on_ready(self):
        print('Bot is online.')
        self.get_data.start()  
                
    @commands.command(name = 'help', aliases = ['h'])
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
        """
        Funny command to see "where" a user is.
        """
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
        """
        Continuously moves a member in and out of a voice channel, spamming them with sound notifications.
        Meant to be use as a funny means to "revive" a defened or afk person.
        
        This command only works if the server has at least 2 voice channels.
        """
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
            
    @commands.command(name = "flips")
    async def flips(self, ctx):
        """
        Prints out flips that are reasonable, in the format of:
        - Item name
        - Buy price
        - Buy volume
        - Sell price
        - Sell volume
        - CPR(coin per hour)
        """
        reasonable_flips = await self.get_reasonable_flips()
        data_str = ""
        for dic in reasonable_flips:
            data_str += f"{dic.get('Item name')}\n"
            data_str += f"Buy price: {dic.get('Buy')}\n"
            data_str += f"Buy volume: {dic.get('1-hr instabuys')}\n"
            data_str += f"Sell: {dic.get('Sell')}\n"
            data_str += f"Sell volume: {dic.get('1-hr instasells')}\n"
            data_str += f"CPR: {dic.get('Coins per hour')}\n\n"
        await ctx.send(data_str)
        
    async def spike_watcher(self, data):
        """
        Function that checks if any of the items in self.watching_list is spiking.
        Prints out the item name and the current buy price if it is spiking, then removes it from the list.
        """
        channel = await self.client.fetch_channel(self.channel_number)
        # it is reasonable to assume that the first 15 items includes the spikes
        for item in self.watching_list:
            for i in range(0, 15):
                if data[i].get("Buy") > self.spike_threshold * data[i].get("Sell"):
                    item_name = data[i].get("Item name")
                    if item in item_name.lower():
                        await channel.send(f"{item_name} is spiking! Current buy price: {data[i].get('Buy')}")
                        self.watching_list.remove(item)
        await self.clean_spiked_items(data[:15])
    
    async def general_spikes(self, data):
        """
        Function that checks if any of the items in the top 15 are spiking.
        Prints out the item name and the current buy price if it is spiking.
        """
        channel = await self.client.fetch_channel(self.channel_number)
        for i in range(0, 15):
            if data[i].get("Buy") > self.spike_threshold * data[i].get("Sell"):
                item_name = data[i].get("Item name")
                if item_name not in self.spiked_items:
                    self.spiked_items.append(item_name)
                    await channel.send(f"{item_name} is spiking! Current buy price: {data[i].get('Buy')}")
        await self.clean_spiked_items(data[:15])
    
    async def clean_spiked_items(self, top_15):
        """
        Function that removes items from self.spiked_items if they are no longer in the top_15, i.e. they are no longer spiking.
        """
        for item in self.spiked_items:
            get_rid = True
            for dic in top_15:
                if item in dic.get("Item name"):
                    get_rid = False
            if get_rid:
                self.spiked_items.remove(item)
    
    @tasks.loop(seconds=60) # change this to change how often the bot updates the data
    async def get_data(self):
        """
        Function that gets the data from Bazaar meta website and returns it as a list of dictionaries in the format of:
        - Item name
        - Buy price
        - Buy volume
        - Sell price
        - Sell volume
        - CPR(coin per hour)
        
        If you wish to use a different website, you can change the url and the way the data is parsed.
        """
        url = "https://www.skyblock.bz/flips"
        print("Getting data from " + url)
        driver = webdriver.Edge()
        driver.get(url)
        time.sleep(1)

        html = driver.page_source
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.find_all("div", class_="card svelte-ln9euk") # do not change this if you are using the same website

        data = []
        for i in range(0, 35): # change this to however many items you want to check, currently 35 as anything more makes around only 5 million coins per hour
            item_name = cards[i].find("div", class_="item-name svelte-ln9euk")
            if(item_name):
                item_info = cards[i].find("p", class_="card_menu svelte-ln9euk")
                item_split = item_info.text.split(" ")
                temp = {}
                item_info_names = ["Item name", "Buy", "1-hr instabuys", "Sell", "1-hr instasells", "Margin", "Coins per hour"]
                temp[item_info_names[0]] = item_name.text
                i = 1
                for item in item_split:
                    new_item = item.replace(",", "")
                    try:
                        temp[item_info_names[i]] = float(new_item)
                        i += 1
                    except:
                        pass
                data.append(temp)
                
        self.data = data
        driver.quit()
        await self.spike_watcher(data)
        await self.general_spikes(data)
    
    async def get_reasonable_flips(self):
        """
        Function that returns a list of flips that are reasonable from the data.
        Reasonable flips are flips that have a buy volume and sell volume of over self.reasonable_buy_volume and self.reasonable_sell_volume respectively. 
        This is done so there is less competition.
        """
        reasonable_flips = []
        for flip in self.data:
            if(flip["1-hr instabuys"] > self.reasonable_buy_volume and flip["1-hr instasells"] > self.reasonable_sell_volume): 
                reasonable_flips.append(flip)
        return reasonable_flips
        
async def setup(bot):
    await bot.add_cog(Main_commands(bot))
    
