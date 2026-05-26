import discord
from discord.ext import commands
from discord import app_commands
import yt_dlp as youtube_dl
import asyncio
from collections import deque
from settings import MUSIC_CONFIG

ydl_opts = {
    'format': 'bestaudio/best',
    'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
    'quiet': True, 'no_warnings': True,
}

FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}

class MusicQueue:
    def __init__(self):
        self.queue = deque()
        self.current = None
        self.loop = False
    def add(self, song):
        if len(self.queue) >= MUSIC_CONFIG["max_queue_size"]: return False
        self.queue.append(song); return True
    def next(self):
        if self.loop and self.current: return self.current
        if self.queue: self.current = self.queue.popleft(); return self.current
        self.current = None; return None
    def clear(self): self.queue.clear(); self.current = None

class MusicSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queues = {}
        self.now_playing = {}
    def get_queue(self, guild_id: int) -> MusicQueue:
        if guild_id not in self.queues: self.queues[guild_id] = MusicQueue()
        return self.queues[guild_id]
    async def search_song(self, query: str):
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            try:
                if query.startswith(("https://", "http://")):
                    info = ydl.extract_info(query, download=False)
                else:
                    info = ydl.extract_info(f"ytsearch:{query}", download=False)
                    if 'entries' in info: info = info['entries'][0]
                return {'title': info.get('title', 'Unknown'), 'url': info.get('webpage_url', info.get('url')), 'duration': info.get('duration', 0), 'thumbnail': info.get('thumbnail'), 'uploader': info.get('uploader', 'Unknown'), 'requester': None}
            except: return None
    async def play_song(self, interaction: discord.Interaction, song: dict):
        guild = interaction.guild
        voice_client = guild.voice_client
        if not voice_client:
            if interaction.user.voice: await interaction.user.voice.channel.connect()
            else: await interaction.followup.send("❌ يجب أن تكون في قناة صوتية!"); return
        song['requester'] = interaction.user
        source = await discord.FFmpegOpusAudio.from_probe(song['url'], **FFMPEG_OPTIONS)
        def after_playing(error): asyncio.run_coroutine_threadsafe(self.play_next(guild), self.bot.loop)
        voice_client.play(source, after=after_playing)
        self.now_playing[guild.id] = song
        embed = discord.Embed(title="🎵 الآن يتم التشغيل", description=f"**[{song['title']}]({song['url']})**", color=discord.Color.green())
        if song.get('thumbnail'): embed.set_thumbnail(url=song['thumbnail'])
        duration_str = f"{song['duration'] // 60}:{song['duration'] % 60:02d}"
        embed.add_field(name="⏱️ المدة", value=duration_str, inline=True)
        embed.add_field(name="👤 طلب بواسطة", value=song['requester'].mention, inline=True)
        await interaction.followup.send(embed=embed)
    async def play_next(self, guild: discord.Guild):
        queue = self.get_queue(guild.id)
        next_song = queue.next()
        if next_song and guild.voice_client:
            source = await discord.FFmpegOpusAudio.from_probe(next_song['url'], **FFMPEG_OPTIONS)
            def after_playing(error): asyncio.run_coroutine_threadsafe(self.play_next(guild), self.bot.loop)
            guild.voice_client.play(source, after=after_playing)
            self.now_playing[guild.id] = next_song
        else:
            await asyncio.sleep(MUSIC_CONFIG["auto_disconnect_minutes"] * 60)
            if guild.voice_client and not guild.voice_client.is_playing():
                await guild.voice_client.disconnect()
                self.now_playing.pop(guild.id, None)

    @app_commands.command(name="play", description="تشغيل أغنية")
    async def play(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()
        if not interaction.user.voice: await interaction.followup.send("❌ يجب أن تكون في قناة صوتية!"); return
        song = await self.search_song(query)
        if not song: await interaction.followup.send("❌ لم يتم العثور على الأغنية!"); return
        queue = self.get_queue(interaction.guild_id)
        voice_client = interaction.guild.voice_client
        if voice_client and voice_client.is_playing():
            if queue.add(song): await interaction.followup.send(f"✅ تمت إضافة **{song['title']}** إلى قائمة الانتظار")
            else: await interaction.followup.send("❌ قائمة الانتظار ممتلئة!")
        else: await self.play_song(interaction, song)

    @app_commands.command(name="skip", description="تخطي الأغنية")
    async def skip(self, interaction: discord.Interaction):
        voice_client = interaction.guild.voice_client
        if not voice_client or not voice_client.is_playing(): await interaction.response.send_message("❌ لا توجد أغنية!"); return
        voice_client.stop()
        await interaction.response.send_message("⏭️ تم تخطي الأغنية!")

    @app_commands.command(name="pause", description="إيقاف مؤقت")
    async def pause(self, interaction: discord.Interaction):
        voice_client = interaction.guild.voice_client
        if voice_client and voice_client.is_playing(): voice_client.pause(); await interaction.response.send_message("⏸️ تم الإيقاف المؤقت")
        else: await interaction.response.send_message("❌ لا توجد أغنية!")

    @app_commands.command(name="resume", description="استئناف")
    async def resume(self, interaction: discord.Interaction):
        voice_client = interaction.guild.voice_client
        if voice_client and voice_client.is_paused(): voice_client.resume(); await interaction.response.send_message("▶️ تم الاستئناف")
        else: await interaction.response.send_message("❌ لا توجد أغنية متوقفة!")

    @app_commands.command(name="queue", description="قائمة الانتظار")
    async def show_queue(self, interaction: discord.Interaction):
        queue = self.get_queue(interaction.guild_id)
        embed = discord.Embed(title="📋 قائمة الانتظار", color=discord.Color.purple())
        current = self.now_playing.get(interaction.guild_id)
        if current: embed.add_field(name="🎵 الآن يتم التشغيل", value=f"**{current['title']}**", inline=False)
        if queue.queue:
            text = ""
            for i, song in enumerate(list(queue.queue)[:10], 1): text += f"{i}. **{song['title']}**\n"
            if len(queue.queue) > 10: text += f"\n... و {len(queue.queue) - 10} أغنية أخرى"
            embed.add_field(name="⏩ القادمة", value=text, inline=False)
        else: embed.add_field(name="⏩ القادمة", value="لا توجد أغاني", inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="stop", description="إيقاف ومغادرة")
    async def stop(self, interaction: discord.Interaction):
        voice_client = interaction.guild.voice_client
        if voice_client:
            self.get_queue(interaction.guild_id).clear()
            voice_client.stop(); await voice_client.disconnect()
            await interaction.response.send_message("⏹️ تم إيقاف الموسيقى")
        else: await interaction.response.send_message("❌ البوت غير متصل!")

    @app_commands.command(name="loop", description="تكرار الأغنية")
    async def loop(self, interaction: discord.Interaction):
        queue = self.get_queue(interaction.guild_id)
        queue.loop = not queue.loop
        await interaction.response.send_message(f"🔄 تم {'تفعيل' if queue.loop else 'تعطيل'} التكرار")

async def setup(bot):
    await bot.add_cog(MusicSystem(bot))