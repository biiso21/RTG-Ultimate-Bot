import aiosqlite
from settings import DATABASE_PATH

async def get_db():
    return await aiosqlite.connect(DATABASE_PATH)

async def init_db():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # جداول المستويات
        await db.execute('''CREATE TABLE IF NOT EXISTS leveling (user_id INTEGER, guild_id INTEGER, xp INTEGER DEFAULT 0, level INTEGER DEFAULT 0, total_messages INTEGER DEFAULT 0, voice_minutes INTEGER DEFAULT 0, last_message_time TEXT, PRIMARY KEY (user_id, guild_id))''')
        # جداول الاقتصاد
        await db.execute('''CREATE TABLE IF NOT EXISTS economy (user_id INTEGER, guild_id INTEGER, balance INTEGER DEFAULT 0, daily_streak INTEGER DEFAULT 0, last_daily TEXT, job TEXT DEFAULT '🍔 Burger Flipper', job_level INTEGER DEFAULT 1, PRIMARY KEY (user_id, guild_id))''')
        # جداول التحذيرات
        await db.execute('''CREATE TABLE IF NOT EXISTS warnings (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, guild_id INTEGER, moderator_id INTEGER, reason TEXT, timestamp TEXT)''')
        # جداول التذاكر
        await db.execute('''CREATE TABLE IF NOT EXISTS tickets (ticket_id TEXT PRIMARY KEY, guild_id INTEGER, user_id INTEGER, channel_id INTEGER, status TEXT, created_at TEXT, transcript TEXT)''')
        # جداول السحوبات
        await db.execute('''CREATE TABLE IF NOT EXISTS giveaways (message_id INTEGER PRIMARY KEY, guild_id INTEGER, channel_id INTEGER, prize TEXT, winners_count INTEGER, end_time TEXT, entries TEXT, ended INTEGER DEFAULT 0)''')
        # جداول المتجر
        await db.execute('''CREATE TABLE IF NOT EXISTS shop (item_id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER, item_name TEXT, role_id INTEGER, price INTEGER, description TEXT)''')
        # جداول الإعدادات
        await db.execute('''CREATE TABLE IF NOT EXISTS level_settings (guild_id INTEGER PRIMARY KEY, announce_channel_id INTEGER, announce_enabled INTEGER DEFAULT 1)''')
        await db.execute('''CREATE TABLE IF NOT EXISTS welcome_settings (guild_id INTEGER PRIMARY KEY, channel_id INTEGER, welcome_enabled INTEGER DEFAULT 1, farewell_enabled INTEGER DEFAULT 1)''')
        await db.execute('''CREATE TABLE IF NOT EXISTS antinuke_settings (guild_id INTEGER PRIMARY KEY, enabled INTEGER DEFAULT 0, log_channel_id INTEGER)''')
        await db.execute('''CREATE TABLE IF NOT EXISTS server_backups (id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER, backup_data TEXT, created_at TEXT)''')
        await db.commit()