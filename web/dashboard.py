import discord
from discord.ext import commands
import aiosqlite
from flask import render_template, request, jsonify
from .app import app

class WebDashboard:
    """لوحة تحكم الويب - إدارة السيرفر من المتصفح"""
    
    def __init__(self, bot):
        self.bot = bot
    
    async def get_server_settings(self, guild_id: int):
        """جلب إعدادات السيرفر"""
        async with aiosqlite.connect("data/rtg_bot.db") as db:
            # إعدادات المستويات
            async with db.execute("SELECT announce_channel_id, announce_enabled FROM level_settings WHERE guild_id = ?", (guild_id,)) as cursor:
                level_settings = await cursor.fetchone()
            
            # إعدادات الترحيب
            async with db.execute("SELECT channel_id, welcome_enabled, farewell_enabled FROM welcome_settings WHERE guild_id = ?", (guild_id,)) as cursor:
                welcome_settings = await cursor.fetchone()
            
            # إعدادات الحماية
            async with db.execute("SELECT enabled, log_channel_id FROM antinuke_settings WHERE guild_id = ?", (guild_id,)) as cursor:
                antinuke_settings = await cursor.fetchone()
        
        return {
            'leveling': {
                'announce_channel': level_settings[0] if level_settings else None,
                'announce_enabled': bool(level_settings[1]) if level_settings else True
            },
            'welcome': {
                'channel': welcome_settings[0] if welcome_settings else None,
                'welcome_enabled': bool(welcome_settings[1]) if welcome_settings else True,
                'farewell_enabled': bool(welcome_settings[2]) if welcome_settings else True
            },
            'antinuke': {
                'enabled': bool(antinuke_settings[0]) if antinuke_settings else False,
                'log_channel': antinuke_settings[1] if antinuke_settings else None
            }
        }
    
    async def update_server_settings(self, guild_id: int, category: str, settings: dict):
        """تحديث إعدادات السيرفر"""
        async with aiosqlite.connect("data/rtg_bot.db") as db:
            if category == 'leveling':
                await db.execute('''INSERT INTO level_settings (guild_id, announce_channel_id, announce_enabled)
                    VALUES (?, ?, ?) ON CONFLICT(guild_id) DO UPDATE SET
                    announce_channel_id = excluded.announce_channel_id,
                    announce_enabled = excluded.announce_enabled''',
                    (guild_id, settings.get('announce_channel'), int(settings.get('announce_enabled', True))))
            
            elif category == 'welcome':
                await db.execute('''INSERT INTO welcome_settings (guild_id, channel_id, welcome_enabled, farewell_enabled)
                    VALUES (?, ?, ?, ?) ON CONFLICT(guild_id) DO UPDATE SET
                    channel_id = excluded.channel_id,
                    welcome_enabled = excluded.welcome_enabled,
                    farewell_enabled = excluded.farewell_enabled''',
                    (guild_id, settings.get('channel'), int(settings.get('welcome_enabled', True)), int(settings.get('farewell_enabled', True))))
            
            elif category == 'antinuke':
                await db.execute('''INSERT INTO antinuke_settings (guild_id, enabled, log_channel_id)
                    VALUES (?, ?, ?) ON CONFLICT(guild_id) DO UPDATE SET
                    enabled = excluded.enabled,
                    log_channel_id = excluded.log_channel_id''',
                    (guild_id, int(settings.get('enabled', False)), settings.get('log_channel')))
            
            await db.commit()
    
    async def get_economy_leaderboard(self, guild_id: int, limit: int = 10):
        """جلب قائمة الأغنياء"""
        async with aiosqlite.connect("data/rtg_bot.db") as db:
            async with db.execute(
                "SELECT user_id, balance FROM economy WHERE guild_id = ? ORDER BY balance DESC LIMIT ?",
                (guild_id, limit)
            ) as cursor:
                return await cursor.fetchall()
    
    async def get_level_leaderboard(self, guild_id: int, limit: int = 10):
        """جلب قائمة المتصدرين في المستويات"""
        async with aiosqlite.connect("data/rtg_bot.db") as db:
            async with db.execute(
                "SELECT user_id, level, xp FROM leveling WHERE guild_id = ? ORDER BY level DESC LIMIT ?",
                (guild_id, limit)
            ) as cursor:
                return await cursor.fetchall()
    
    async def add_shop_item_web(self, guild_id: int, name: str, price: int, role_id: int = None, description: str = ""):
        """إضافة منتج إلى المتجر من الويب"""
        async with aiosqlite.connect("data/rtg_bot.db") as db:
            await db.execute('''INSERT INTO shop (guild_id, item_name, role_id, price, description)
                VALUES (?, ?, ?, ?, ?)''', (guild_id, name, role_id, price, description))
            await db.commit()
        return True
    
    async def get_shop_items(self, guild_id: int):
        """جلب منتجات المتجر"""
        async with aiosqlite.connect("data/rtg_bot.db") as db:
            async with db.execute("SELECT item_id, item_name, price, description FROM shop WHERE guild_id = ?", (guild_id,)) as cursor:
                return await cursor.fetchall()