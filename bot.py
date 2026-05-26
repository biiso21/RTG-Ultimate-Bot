# ========== تهيئة قاعدة البيانات ==========
from utils.database import init_db

# تشغيل تهيئة قاعدة البيانات عند بدء البوت
async def setup_database():
    await init_db()
    print("✅ قاعدة البيانات جاهزة")

# تشغيل التهيئة
asyncio.create_task(setup_database())
# ========================================
import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import logging
import os
import json
import threading
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ========== إنشاء المجلدات بأمان ==========
for folder in ["data", "data/backups", "logs"]:
    if not os.path.exists(folder):
        os.makedirs(folder)
        print(f"✅ تم إنشاء مجلد: {folder}")

# ========== خادم ويب لإبقاء البوت نشطاً ==========
from flask import Flask

web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "✅ RTG Ultimate Bot is running!"

@web_app.route('/ping')
def ping():
    return "pong", 200

def run_web():
    web_app.run(host='0.0.0.0', port=8080)

threading.Thread(target=run_web, daemon=True).start()
# ============================================

# إعداد التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# إعداد الصلاحيات
intents = discord.Intents.all()
intents.message_content = True
intents.members = True
intents.voice_states = True

TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# ========== إعدادات الحماية ==========
OWNER_ID = int(os.getenv("OWNER_ID", "1276968112071249958"))
OWNER_GUILD_ID = int(os.getenv("OWNER_GUILD_ID", "1361756331404693665"))
ALLOWED_GUILDS = [int(x) for x in os.getenv("ALLOWED_GUILDS", "1361756331404693665").split(",")] if os.getenv("ALLOWED_GUILDS") else []
PROTECTION_MODE = int(os.getenv("PROTECTION_MODE", "0"))

DEV_IDS = [OWNER_ID]

# ========== نظام الترخيص البسيط ==========
class SimpleLicense:
    def __init__(self):
        self.license_file = "license_keys.json"
        self.licenses = self.load_licenses()
    
    def load_licenses(self):
        if os.path.exists(self.license_file):
            try:
                with open(self.license_file, 'r') as f:
                    return json.load(f)
            except:
                return {"licenses": {}, "owner_guild": OWNER_GUILD_ID}
        return {"licenses": {}, "owner_guild": OWNER_GUILD_ID}
    
    def save_licenses(self):
        with open(self.license_file, 'w') as f:
            json.dump(self.licenses, f, indent=4)
    
    def generate_key(self, guild_id: int, guild_name: str):
        import secrets
        key = secrets.token_hex(16).upper()
        self.licenses["licenses"][key] = {
            "guild_id": guild_id,
            "guild_name": guild_name,
            "activated": False,
            "expires": (datetime.now().timestamp() + 365 * 24 * 3600)
        }
        self.save_licenses()
        return key
    
    def activate(self, key: str, guild_id: int):
        if key not in self.licenses["licenses"]:
            return False
        lic = self.licenses["licenses"][key]
        if lic["guild_id"] != guild_id:
            return False
        if lic["expires"] < datetime.now().timestamp():
            return False
        lic["activated"] = True
        self.save_licenses()
        return True
    
    def check(self, guild_id: int):
        if guild_id == OWNER_GUILD_ID:
            return True
        for key, data in self.licenses["licenses"].items():
            if data["guild_id"] == guild_id and data["activated"]:
                if data["expires"] >= datetime.now().timestamp():
                    return True
        return False

license_manager = SimpleLicense()

# ========== البوت الرئيسي ==========
class RTGUltimateBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents, help_command=None)
        self.start_time = datetime.now()
        self.version = "5.0.0 - Protected"
    
    async def setup_hook(self):
        logger.info("🔄 جاري تحميل جميع الوحدات...")
        
        if PROTECTION_MODE == 1:
            await self.check_all_guilds()
        
        cogs_list = [
            "cogs.leveling", "cogs.music", "cogs.antinuke",
            "cogs.economy", "cogs.tickets", "cogs.giveaways",
            "cogs.welcome", "cogs.moderation", "cogs.fun"
        ]
        
        for cog in cogs_list:
            try:
                await self.load_extension(cog)
                logger.info(f"✅ تم تحميل {cog}")
            except Exception as e:
                logger.error(f"❌ فشل تحميل {cog}: {e}")
        
        await self.tree.sync()
        logger.info("✅ تم تجهيز البوت بالكامل!")
    
    async def check_all_guilds(self):
        to_leave = []
        for guild in self.guilds:
            if not license_manager.check(guild.id):
                logger.warning(f"❌ سيرفر غير مرخص: {guild.name}")
                to_leave.append(guild)
        for guild in to_leave:
            try:
                await guild.leave()
                logger.info(f"🚪 غادر البوت السيرفر: {guild.name}")
            except:
                pass
    
    async def on_guild_join(self, guild: discord.Guild):
        if PROTECTION_MODE == 1:
            if license_manager.check(guild.id):
                logger.info(f"✅ انضم لسيرفر مرخص: {guild.name}")
                channel = guild.system_channel or guild.text_channels[0]
                if channel:
                    embed = discord.Embed(
                        title="🎉 شكراً لاختيار RTG Ultimate Bot!",
                        description="البوت مفعل ومرخص بشكل رسمي.\nاستخدم `/help` لعرض جميع الأوامر.",
                        color=discord.Color.green()
                    )
                    await channel.send(embed=embed)
            else:
                logger.warning(f"⚠️ انضم لسيرفر غير مرخص: {guild.name}")
                channel = guild.system_channel or guild.text_channels[0]
                if channel:
                    embed = discord.Embed(
                        title="🔒 البوت بحاجة إلى تفعيل",
                        description="هذا السيرفر غير مرخص!\nللتفعيل استخدم `/activate`",
                        color=discord.Color.orange()
                    )
                    await channel.send(embed=embed)
                await asyncio.sleep(60)
                if not license_manager.check(guild.id):
                    await guild.leave()

bot = RTGUltimateBot()

# ========== أوامر الترخيص ==========
@bot.tree.command(name="activate", description="تفعيل البوت على هذا السيرفر")
async def activate_bot(interaction: discord.Interaction, license_key: str):
    guild_id = interaction.guild_id
    if license_manager.check(guild_id):
        await interaction.response.send_message("✅ البوت مفعل بالفعل!", ephemeral=True)
        return
    if license_manager.activate(license_key, guild_id):
        embed = discord.Embed(title="✅ تم تفعيل البوت بنجاح!", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message("❌ مفتاح التفعيل غير صالح!", ephemeral=True)

@bot.tree.command(name="license_info", description="عرض معلومات الترخيص")
async def license_info(interaction: discord.Interaction):
    guild_id = interaction.guild_id
    is_licensed = license_manager.check(guild_id)
    status = "✅ مفعل" if is_licensed else "❌ غير مرخص"
    embed = discord.Embed(title="🔑 معلومات الترخيص", description=f"**الحالة:** {status}", color=discord.Color.green() if is_licensed else discord.Color.red())
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ========== أحداث البوت الأساسية ==========
@bot.event
async def on_ready():
    logger.info(f"✅ {bot.user} متصل!")
    logger.info(f"📊 موجود في {len(bot.guilds)} سيرفر")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="RTG Community | /help"))

@bot.tree.command(name="help", description="عرض جميع أوامر البوت")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(title="🎮 RTG Ultimate Bot - المساعدة", color=discord.Color.purple())
    embed.add_field(name="💰 الاقتصاد", value="`/balance`, `/daily`, `/work`, `/pay`, `/shop`, `/buy`, `/slots`", inline=False)
    embed.add_field(name="📈 المستويات", value="`/rank`, `/leaderboard`", inline=False)
    embed.add_field(name="🎵 الموسيقى", value="`/play`, `/skip`, `/pause`, `/resume`, `/queue`", inline=False)
    embed.add_field(name="🎫 التذاكر", value="`/ticket_panel`, `/ticket_close`", inline=False)
    embed.add_field(name="🎁 السحوبات", value="`/giveaway_create`", inline=False)
    embed.add_field(name="🛡️ الإدارة", value="`/clear`, `/ban`, `/kick`, `/mute`", inline=False)
    embed.add_field(name="🔐 الترخيص", value="`/activate`, `/license_info`", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

if __name__ == "__main__":
    if not TOKEN or TOKEN == "ضع_توكن_البوت_هنا":
        print("❌ خطأ: لم يتم إدخال توكن البوت!")
    else:
        bot.run(TOKEN)
