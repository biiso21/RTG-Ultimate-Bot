import discord
from discord.ext import commands, tasks
from discord import app_commands
import aiosqlite
import random
import math
from datetime import datetime
from settings import LEVELING_CONFIG, LEVEL_AWARDS

class LevelingSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cooldowns = {}
        self.voice_xp_cooldowns = {}

    async def cog_load(self):
        async with aiosqlite.connect("data/rtg_bot.db") as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS leveling (
                    user_id INTEGER, guild_id INTEGER,
                    xp INTEGER DEFAULT 0, level INTEGER DEFAULT 0,
                    total_messages INTEGER DEFAULT 0,
                    voice_minutes INTEGER DEFAULT 0,
                    last_message_time TEXT,
                    PRIMARY KEY (user_id, guild_id)
                )
            ''')
            await db.execute('''
                CREATE TABLE IF NOT EXISTS level_settings (
                    guild_id INTEGER PRIMARY KEY,
                    announce_channel_id INTEGER,
                    announce_enabled INTEGER DEFAULT 1
                )
            ''')
            await db.commit()

    def calculate_level(self, xp: int) -> int:
        if xp <= 0: return 0
        return int((math.sqrt(200 * xp + 2500) - 50) / 100)

    async def add_xp(self, user_id: int, guild_id: int, amount: int, source: str = "message"):
        async with aiosqlite.connect("data/rtg_bot.db") as db:
            async with db.execute("SELECT xp, level FROM leveling WHERE user_id = ? AND guild_id = ?", (user_id, guild_id)) as cursor:
                result = await cursor.fetchone()
            if result:
                current_xp, current_level = result
                new_xp = current_xp + amount
            else:
                current_xp, current_level = 0, 0
                new_xp = amount
            new_level = self.calculate_level(new_xp)
            if source == "message":
                await db.execute('''INSERT INTO leveling (user_id, guild_id, xp, level, total_messages, last_message_time)
                    VALUES (?, ?, ?, ?, 1, ?) ON CONFLICT(user_id, guild_id) DO UPDATE SET
                    xp = excluded.xp, level = excluded.level, total_messages = total_messages + 1,
                    last_message_time = excluded.last_message_time''', (user_id, guild_id, new_xp, new_level, datetime.now().isoformat()))
            else:
                await db.execute('''INSERT INTO leveling (user_id, guild_id, xp, level, voice_minutes)
                    VALUES (?, ?, ?, ?, 1) ON CONFLICT(user_id, guild_id) DO UPDATE SET
                    xp = xp + ?, level = excluded.level, voice_minutes = voice_minutes + 1''',
                    (user_id, guild_id, new_xp, new_level, amount))
            await db.commit()
            if new_level > current_level:
                await self.handle_level_up(guild_id, user_id, current_level, new_level)
                await self.award_coins(user_id, guild_id, new_level * 50)
            return new_level, new_xp

    async def handle_level_up(self, guild_id: int, user_id: int, old_level: int, new_level: int):
        guild = self.bot.get_guild(guild_id)
        if not guild: return
        member = guild.get_member(user_id)
        if not member: return
        async with aiosqlite.connect("data/rtg_bot.db") as db:
            async with db.execute("SELECT announce_channel_id FROM level_settings WHERE guild_id = ?", (guild_id,)) as cursor:
                result = await cursor.fetchone()
        channel = guild.get_channel(result[0]) if result and result[0] else guild.system_channel
        if channel and LEVELING_CONFIG.get("announce_level_up", True):
            embed = discord.Embed(title=f"🎉 {member.display_name} وصل إلى مستوى جديد! 🎉", description=f"المستوى **{new_level}** 🏆", color=discord.Color.gold())
            await channel.send(embed=embed)
        for award in LEVEL_AWARDS:
            if new_level >= award["level"]:
                role = discord.utils.get(guild.roles, name=award["role_name"])
                if role and role not in member.roles:
                    await member.add_roles(role)

    async def award_coins(self, user_id: int, guild_id: int, amount: int):
        async with aiosqlite.connect("data/rtg_bot.db") as db:
            await db.execute('''INSERT INTO economy (user_id, guild_id, balance) VALUES (?, ?, ?)
                ON CONFLICT(user_id, guild_id) DO UPDATE SET balance = balance + ?''', (user_id, guild_id, amount, amount))
            await db.commit()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild: return
        now = datetime.now().timestamp()
        key = f"{message.guild.id}_{message.author.id}"
        if key in self.cooldowns and now - self.cooldowns[key] < LEVELING_CONFIG["per"]: return
        self.cooldowns[key] = now
        xp_gain = LEVELING_CONFIG["base_xp"] + random.randint(0, LEVELING_CONFIG["random_xp"])
        await self.add_xp(message.author.id, message.guild.id, xp_gain, "message")

    @tasks.loop(seconds=LEVELING_CONFIG["voice_xp_interval"])
    async def voice_xp_loop(self):
        if not LEVELING_CONFIG.get("voice_xp_enabled", True): return
        for guild in self.bot.guilds:
            for voice_channel in guild.voice_channels:
                for member in voice_channel.members:
                    if member.bot: continue
                    now = datetime.now().timestamp()
                    key = f"voice_{guild.id}_{member.id}"
                    if key in self.voice_xp_cooldowns and now - self.voice_xp_cooldowns[key] < LEVELING_CONFIG["voice_xp_interval"]: continue
                    self.voice_xp_cooldowns[key] = now
                    await self.add_xp(member.id, guild.id, LEVELING_CONFIG["voice_xp_amount"], "voice")

    @app_commands.command(name="rank", description="عرض رتبتك")
    async def show_rank(self, interaction: discord.Interaction, member: discord.Member = None):
        target = member or interaction.user
        async with aiosqlite.connect("data/rtg_bot.db") as db:
            async with db.execute("SELECT xp, level, total_messages, voice_minutes FROM leveling WHERE user_id = ? AND guild_id = ?", (target.id, interaction.guild_id)) as cursor:
                result = await cursor.fetchone()
        if not result: xp, level, messages, voice_mins = 0, 0, 0, 0
        else: xp, level, messages, voice_mins = result
        embed = discord.Embed(title=f"📊 رتبة {target.display_name}", color=discord.Color.blue())
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="🏆 المستوى", value=f"**{level}**", inline=True)
        embed.add_field(name="✨ الخبرة", value=f"**{xp}** XP", inline=True)
        embed.add_field(name="💬 الرسائل", value=f"**{messages}**", inline=True)
        embed.add_field(name="🎙️ وقت الصوتي", value=f"**{voice_mins}** دقيقة", inline=True)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="leaderboard", description="قائمة المتصدرين")
    async def level_leaderboard(self, interaction: discord.Interaction, type: str = "level"):
        type = type.lower()
        async with aiosqlite.connect("data/rtg_bot.db") as db:
            if type == "messages":
                async with db.execute("SELECT user_id, total_messages FROM leveling WHERE guild_id = ? ORDER BY total_messages DESC LIMIT 10", (interaction.guild_id,)) as cursor:
                    results = await cursor.fetchall()
                title = "💬 أكثر الأعضاء رسائلًا"
            else:
                async with db.execute("SELECT user_id, level, xp FROM leveling WHERE guild_id = ? ORDER BY level DESC, xp DESC LIMIT 10", (interaction.guild_id,)) as cursor:
                    results = await cursor.fetchall()
                title = "🏆 أعلى المستويات"
        embed = discord.Embed(title=title, color=discord.Color.gold())
        if not results: embed.description = "لا توجد بيانات كافية بعد!"
        else:
            text = ""
            for i, row in enumerate(results, 1):
                member = interaction.guild.get_member(row[0])
                name = member.display_name if member else f"مستخدم #{row[0]}"
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                text += f"{medal} **{name}** - المستوى {row[1]}\n" if type != "messages" else f"{medal} **{name}** - {row[1]} رسالة\n"
            embed.description = text
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="set_level_channel", description="[ADMIN] تعيين قناة الإعلانات")
    @app_commands.default_permissions(administrator=True)
    async def set_level_channel(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        channel_id = channel.id if channel else None
        async with aiosqlite.connect("data/rtg_bot.db") as db:
            await db.execute('''INSERT INTO level_settings (guild_id, announce_channel_id) VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET announce_channel_id = excluded.announce_channel_id''', (interaction.guild_id, channel_id))
            await db.commit()
        embed = discord.Embed(title="✅ تم التعيين", description=f"سيتم إرسال الإعلانات إلى {channel.mention if channel else 'القناة الافتراضية'}", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(LevelingSystem(bot))