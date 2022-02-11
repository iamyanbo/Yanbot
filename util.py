from urllib import request
from urllib.error import HTTPError
from urllib.parse import urlparse
import youtube_dl
import concurrent.futures
import asyncio
import re

pattern_url = re.compile(r'^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$')
def is_url(url: str) -> bool:
    return pattern_url.match(url) is not None

async def youtube_extract_info(url, playlist = False):
    def _extract(_url):
        try:
            if playlist:
                opts = {'default_search': 'auto',
                'format' :'--yes-playlist, bestaudio',
                'forceduration': True}
                with youtube_dl.YoutubeDL(opts) as ydl:
                    return ydl.extract_info(_url, download=False)
            else:
                opts = {'default_search': 'auto',
                'format' :'--no-playlist, bestaudio',
                'forceduration': True,
                'noplaylist': True}
                with youtube_dl.YoutubeDL(opts) as ydl:
                    return ydl.extract_info(_url, download=False)
        except HTTPError:
            return None
    loop = asyncio.get_running_loop()
    with concurrent.futures.ThreadPoolExecutor() as pool:
        return await loop.run_in_executor(pool, _extract, url)