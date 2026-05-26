# التأكد من وجود مجلد البيانات
import os
os.makedirs("data", exist_ok=True)
os.makedirs("data/backups", exist_ok=True)
os.makedirs("logs", exist_ok=True)
# ========== خادم ويب لإبقاء البوت نشطاً على Render ==========
from flask import Flask
import threading

web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "✅ RTG Ultimate Bot is running!"

@web_app.route('/ping')
def ping():
    return "pong", 200

def run_web():
    web_app.run(host='0.0.0.0', port=8080)

# تشغيل خادم الويب في خيط منفصل
threading.Thread(target=run_web, daemon=True).start()
# ============================================================
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
OWNER_ID = 1276968112071249958  # حسابك
OWNER_GUILD_ID = 1361756331404693665  # سيرفرك
ALLOWED_GUILDS = [1361756331404693665]  # السيرفرات المسموحة
PROTECTION_MODE = True

# قائمة المطورين
DEV_IDS = [1276968112071249958]

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
        # السيرفر الأساسي للمطور دائماً مسموح
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
        
        # التحقق من الترخيص قبل التحميل
        if PROTECTION_MODE:
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
        """التحقق من جميع السيرفرات"""
        to_leave = []
        for guild in self.guilds:
            if not license_manager.check(guild.id):
                logger.warning(f"❌ سيرفر غير مرخص: {guild.name} ({guild.id})")
                to_leave.append(guild)
        
        for guild in to_leave:
            try:
                await guild.leave()
                logger.info(f"🚪 غادر البوت السيرفر: {guild.name}")
            except:
                pass
    
    async def on_guild_join(self, guild: discord.Guild):
        """عند إضافة البوت لسيرفر جديد"""
        if PROTECTION_MODE:
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
                        description="هذا السيرفر غير مرخص!\n\nللتفعيل، استخدم:\n`/activate <مفتاح_الترخيص>`\n\nللحصول على مفتاح، تواصل مع المطور.",
                        color=discord.Color.orange()
                    )
                    await channel.send(embed=embed)
                
                await asyncio.sleep(60)
                if not license_manager.check(guild.id):
                    await guild.leave()
                    logger.info(f"🚪 غادر البوت السيرفر: {guild.name}")

bot = RTGUltimateBot()

# ========== أوامر الترخيص ==========
@bot.tree.command(name="generate_license", description="[OWNER] توليد مفتاح ترخيص")
async def generate_license(interaction: discord.Interaction, guild_id: str, expires_days: int = 365):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("❌ هذا الأمر للمطور فقط!", ephemeral=True)
        return
    
    try:
        guild_id_int = int(guild_id)
        guild = bot.get_guild(guild_id_int)
        guild_name = guild.name if guild else f"Guild_{guild_id_int}"
        
        key = license_manager.generate_key(guild_id_int, guild_name)
        
        embed = discord.Embed(
            title="🔑 مفتاح ترخيص جديد",
            description=f"**للسيرفر:** {guild_name}\n**المعرف:** {guild_id_int}",
            color=discord.Color.green()
        )
        embed.add_field(name="مفتاح التفعيل", value=f"`{key}`", inline=False)
        embed.add_field(name="مدة الصلاحية", value=f"{expires_days} يوم", inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # إرسال للمطور خاص
        owner = await bot.fetch_user(OWNER_ID)
        if owner:
            await owner.send(f"🔑 **مفتاح ترخيص جديد**\nالسيرفر: {guild_name}\nالمعرف: `{guild_id_int}`\nالمفتاح: `{key}`")
    
    except ValueError:
        await interaction.response.send_message("❌ معرف السيرفر غير صالح!", ephemeral=True)

@bot.tree.command(name="activate", description="تفعيل البوت على هذا السيرفر")
async def activate_bot(interaction: discord.Interaction, license_key: str):
    guild_id = interaction.guild_id
    
    if license_manager.check(guild_id):
        await interaction.response.send_message("✅ البوت مفعل بالفعل!", ephemeral=True)
        return
    
    if license_manager.activate(license_key, guild_id):
        embed = discord.Embed(
            title="✅ تم تفعيل البوت بنجاح!",
            description="شكراً لتفعيل RTG Ultimate Bot على سيرفرك! 🎉",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)
        
        # إشعار للمطور
        owner = await bot.fetch_user(OWNER_ID)
        if owner:
            await owner.send(f"✅ **تم تفعيل البوت**\nالسيرفر: {interaction.guild.name}\nالمعرف: `{guild_id}`\nبواسطة: {interaction.user.name}")
    else:
        await interaction.response.send_message("❌ مفتاح التفعيل غير صالح!", ephemeral=True)

@bot.tree.command(name="license_info", description="عرض معلومات الترخيص")
async def license_info(interaction: discord.Interaction):
    guild_id = interaction.guild_id
    is_licensed = license_manager.check(guild_id)
    
    if guild_id == OWNER_GUILD_ID:
        embed = discord.Embed(
            title="🔑 معلومات الترخيص",
            description=f"**السيرفر:** {interaction.guild.name}\n**الحالة:** ✅ السيرفر الأساسي للمطور (دائماً مفعل)",
            color=discord.Color.green()
        )
    elif is_licensed:
        embed = discord.Embed(
            title="🔑 معلومات الترخيص",
            description=f"**السيرفر:** {interaction.guild.name}\n**الحالة:** ✅ مفعل ومرخص",
            color=discord.Color.green()
        )
    else:
        embed = discord.Embed(
            title="🔑 معلومات الترخيص",
            description=f"**السيرفر:** {interaction.guild.name}\n**الحالة:** ❌ غير مرخص\n\nاستخدم `/activate` لتفعيل البوت",
            color=discord.Color.red()
        )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ========== أحداث البوت الأساسية ==========
@bot.event
async def on_ready():
    logger.info(f"✅ {bot.user} متصل!")
    logger.info(f"📊 موجود في {len(bot.guilds)} سيرفر")
    logger.info(f"👑 المطور: <@{OWNER_ID}>")
    logger.info(f"🏠 السيرفر الأساسي: {OWNER_GUILD_ID}")
    
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="RTG Community | /help"
        )
    )

@bot.tree.command(name="help", description="عرض جميع أوامر البوت")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(title="🎮 RTG Ultimate Bot - المساعدة الكاملة", color=discord.Color.purple())
    embed.add_field(name="💰 الاقتصاد", value="`/balance`, `/daily`, `/work`, `/pay`, `/shop`, `/buy`, `/slots`, `/steal`", inline=False)
    embed.add_field(name="📈 المستويات", value="`/rank`, `/leaderboard`", inline=False)
    embed.add_field(name="🎵 الموسيقى", value="`/play`, `/skip`, `/pause`, `/resume`, `/queue`, `/stop`", inline=False)
    embed.add_field(name="🎫 التذاكر", value="`/ticket_panel`, `/ticket_close`", inline=False)
    embed.add_field(name="🎁 السحوبات", value="`/giveaway_create`, `/giveaway_reroll`", inline=False)
    embed.add_field(name="🛡️ الإدارة", value="`/clear`, `/ban`, `/kick`, `/mute`, `/warn`, `/lockdown`", inline=False)
    embed.add_field(name="🎭 الترفيه", value="`/hug`, `/kiss`, `/slap`, `/8ball`, `/meme`, `/avatar`", inline=False)
    embed.add_field(name="🔐 الترخيص", value="`/activate`, `/license_info`", inline=False)
    embed.set_footer(text=f"RTG Community | {len(bot.guilds)} سيرفر")
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="stats", description="إحصائيات البوت")
async def bot_stats(interaction: discord.Interaction):
    uptime = datetime.now() - bot.start_time
    uptime_str = f"{uptime.days} يوم {uptime.seconds//3600} ساعة"
    
    embed = discord.Embed(title="📊 إحصائيات RTG Bot", color=discord.Color.blue())
    embed.add_field(name="🟢 الحالة", value="متصل", inline=True)
    embed.add_field(name="⏰ وقت التشغيل", value=uptime_str, inline=True)
    embed.add_field(name="📦 الإصدار", value=f"v{bot.version}", inline=True)
    embed.add_field(name="🌐 عدد السيرفرات", value=str(len(bot.guilds)), inline=True)
    embed.add_field(name="👥 عدد المستخدمين", value=str(len(bot.users)), inline=True)
    
    await interaction.response.send_message(embed=embed)

# ========== أوامر المطور ==========
@bot.tree.command(name="reload", description="[OWNER] إعادة تحميل الوحدات")
async def reload_cogs(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("❌ هذا الأمر للمطور فقط!", ephemeral=True)
        return
    
    await interaction.response.send_message("🔄 جاري إعادة التحميل...", ephemeral=True)
    
    cogs = ["cogs.leveling", "cogs.music", "cogs.antinuke", "cogs.economy", 
            "cogs.tickets", "cogs.giveaways", "cogs.welcome", "cogs.moderation", "cogs.fun"]
    
    for cog in cogs:
        try:
            await bot.reload_extension(cog)
        except Exception as e:
            logger.error(f"فشل إعادة تحميل {cog}: {e}")
    
    await interaction.edit_original_response(content="✅ تم إعادة تحميل جميع الوحدات!")

@bot.tree.command(name="servers", description="[OWNER] عرض قائمة السيرفرات")
async def list_servers(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("❌ هذا الأمر للمطور فقط!", ephemeral=True)
        return
    
    embed = discord.Embed(title="📋 قائمة السيرفرات", color=discord.Color.blue())
    
    for guild in bot.guilds:
        status = "✅" if license_manager.check(guild.id) else "❌"
        embed.add_field(
            name=f"{status} {guild.name}",
            value=f"المعرف: `{guild.id}`\nالأعضاء: {guild.member_count}",
            inline=False
        )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# تشغيل البوت
if __name__ == "__main__":
    if TOKEN == "ضع_توكن_البوت_هنا" or not TOKEN:
        print("❌ خطأ: لم يتم إدخال توكن البوت!")
        print("الرجاء إدخال التوكن في ملف .env")
    else:
        bot.run(TOKEN)