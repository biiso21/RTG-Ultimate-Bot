import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
import asyncio
import json
from datetime import datetime
from collections import defaultdict
from settings import ANTINUKE_CONFIG

class AntiNukeSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.channel_create_log = defaultdict(list)
        self.role_create_log = defaultdict(list)
        self.member_join_log = defaultdict(list)
        self.protection_enabled = {}
        self.log_channels = {}

    async def cog_load(self):
        async with aiosqlite.connect("data/rtg_bot.db") as db:
            await db.execute('''CREATE TABLE IF NOT EXISTS antinuke_settings (guild_id INTEGER PRIMARY KEY, enabled INTEGER DEFAULT 0, log_channel_id INTEGER)''')
            await db.execute('''CREATE TABLE IF NOT EXISTS antinuke_whitelist (guild_id INTEGER, user_id INTEGER, PRIMARY KEY (guild_id, user_id))''')
            await db.execute('''CREATE TABLE IF NOT EXISTS server_backups (id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER, backup_data TEXT, created_at TEXT)''')
            await db.commit()
        async with aiosqlite.connect("data/rtg_bot.db") as db:
            async with db.execute("SELECT guild_id, enabled, log_channel_id FROM antinuke_settings") as cursor:
                async for guild_id, enabled, log_channel_id in cursor:
                    self.protection_enabled[guild_id] = bool(enabled)
                    if log_channel_id: self.log_channels[guild_id] = log_channel_id

    async def log_security(self, guild_id: int, title: str, description: str):
        channel_id = self.log_channels.get(guild_id)
        if not channel_id: return
        guild = self.bot.get_guild(guild_id)
        if guild:
            channel = guild.get_channel(channel_id)
            if channel: await channel.send(embed=discord.Embed(title=title, description=description, color=discord.Color.red(), timestamp=datetime.now()))

    async def take_action(self, guild_id: int, user: discord.Member, action_type: str):
        guild = self.bot.get_guild(guild_id)
        if guild: await guild.ban(user, reason=f"[Auto-Mod] {action_type}")

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        guild = channel.guild
        if not self.protection_enabled.get(guild.id, False): return
        now = datetime.now().timestamp()
        self.channel_create_log[guild.id].append(now)
        self.channel_create_log[guild.id] = [t for t in self.channel_create_log[guild.id] if now - t <= ANTINUKE_CONFIG["time_window"]]
        if len(self.channel_create_log[guild.id]) > ANTINUKE_CONFIG["max_channels_create"]:
            async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.channel_create):
                if entry.target.id == channel.id: await self.take_action(guild.id, entry.user, "Mass channel creation"); break

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        guild = role.guild
        if not self.protection_enabled.get(guild.id, False): return
        now = datetime.now().timestamp()
        self.role_create_log[guild.id].append(now)
        self.role_create_log[guild.id] = [t for t in self.role_create_log[guild.id] if now - t <= ANTINUKE_CONFIG["time_window"]]
        if len(self.role_create_log[guild.id]) > ANTINUKE_CONFIG["max_roles_create"]:
            async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.role_create):
                if entry.target.id == role.id: await self.take_action(guild.id, entry.user, "Mass role creation"); break

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild = member.guild
        if not self.protection_enabled.get(guild.id, False): return
        now = datetime.now().timestamp()
        self.member_join_log[guild.id].append(now)
        self.member_join_log[guild.id] = [t for t in self.member_join_log[guild.id] if now - t <= 30]
        if len(self.member_join_log[guild.id]) > 10:
            for channel in guild.text_channels:
                await channel.set_permissions(guild.default_role, send_messages=False)
            await self.log_security(guild.id, "🛡️ تم تفعيل وضع الحماية", "تم اكتشاف هجوم Raid! تم تعطيل إرسال الرسائل.")
            await asyncio.sleep(300)
            for channel in guild.text_channels:
                await channel.set_permissions(guild.default_role, send_messages=None)

    @app_commands.command(name="antinuke", description="[ADMIN] تفعيل/تعطيل الحماية")
    @app_commands.default_permissions(administrator=True)
    async def toggle_antinuke(self, interaction: discord.Interaction, state: str):
        enabled = state.lower() == "on"
        self.protection_enabled[interaction.guild_id] = enabled
        async with aiosqlite.connect("data/rtg_bot.db") as db:
            await db.execute('''INSERT INTO antinuke_settings (guild_id, enabled) VALUES (?, ?) ON CONFLICT(guild_id) DO UPDATE SET enabled = excluded.enabled''', (interaction.guild_id, int(enabled)))
            await db.commit()
        embed = discord.Embed(title="🛡️ نظام الحماية", description=f"تم {'تفعيل' if enabled else 'تعطيل'}", color=discord.Color.green() if enabled else discord.Color.red())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="set_log_channel", description="[ADMIN] تعيين قناة السجلات")
    @app_commands.default_permissions(administrator=True)
    async def set_log_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        self.log_channels[interaction.guild_id] = channel.id
        async with aiosqlite.connect("data/rtg_bot.db") as db:
            await db.execute('''INSERT INTO antinuke_settings (guild_id, log_channel_id) VALUES (?, ?) ON CONFLICT(guild_id) DO UPDATE SET log_channel_id = excluded.log_channel_id''', (interaction.guild_id, channel.id))
            await db.commit()
        await interaction.response.send_message(f"✅ سيتم إرسال السجلات إلى {channel.mention}")

    @app_commands.command(name="backup", description="[ADMIN] إنشاء نسخة احتياطية")
    @app_commands.default_permissions(administrator=True)
    async def create_backup(self, interaction: discord.Interaction):
        await interaction.response.defer()
        guild = interaction.guild
        backup_data = {"name": guild.name, "roles": [], "channels": [], "created_at": datetime.now().isoformat()}
        for role in guild.roles:
            if role.name != "@everyone":
                backup_data["roles"].append({"name": role.name, "color": role.color.value, "permissions": role.permissions.value})
        for channel in guild.channels:
            if not isinstance(channel, discord.CategoryChannel):
                backup_data["channels"].append({"name": channel.name, "type": str(channel.type)})
        async with aiosqlite.connect("data/rtg_bot.db") as db:
            await db.execute("INSERT INTO server_backups (guild_id, backup_data, created_at) VALUES (?, ?, ?)", (guild.id, json.dumps(backup_data), datetime.now().isoformat()))
            await db.commit()
        await interaction.followup.send(f"✅ تم إنشاء النسخة الاحتياطية! حفظ {len(backup_data['roles'])} رتبة و {len(backup_data['channels'])} قناة")

async def setup(bot):
    await bot.add_cog(AntiNukeSystem(bot))