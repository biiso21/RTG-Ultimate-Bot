import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import logging
import os
import json
import threading
import aiosqlite
import secrets
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask

load_dotenv()

# ========== إنشاء المجلدات ==========
for folder in ["data", "data/backups", "logs"]:
    os.makedirs(folder, exist_ok=True)

# ========== خادم ويب لإبقاء البوت نشطاً ==========
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
    handlers=[logging.FileHandler('logs/bot.log'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

intents = discord.Intents.all()
intents.message_content = True
intents.members = True
intents.voice_states = True

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "1276968112071249958"))
OWNER_GUILD_ID = int(os.getenv("OWNER_GUILD_ID", "1361756331404693665"))
PROTECTION_MODE = int(os.getenv("PROTECTION_MODE", "0"))

# ========== تهيئة قاعدة البيانات ==========
async def init_db():
    async with aiosqlite.connect("data/rtg_bot.db") as db:
        # جدول المستويات
        await db.execute('''CREATE TABLE IF NOT EXISTS leveling (user_id INTEGER, guild_id INTEGER, xp INTEGER DEFAULT 0, level INTEGER DEFAULT 0, total_messages INTEGER DEFAULT 0, voice_minutes INTEGER DEFAULT 0, last_message_time TEXT, PRIMARY KEY (user_id, guild_id))''')
        # جدول الاقتصاد
        await db.execute('''CREATE TABLE IF NOT EXISTS economy (user_id INTEGER, guild_id INTEGER, balance INTEGER DEFAULT 0, daily_streak INTEGER DEFAULT 0, last_daily TEXT, job TEXT DEFAULT '🍔 Burger Flipper', job_level INTEGER DEFAULT 1, PRIMARY KEY (user_id, guild_id))''')
        # جدول السحوبات
        await db.execute('''CREATE TABLE IF NOT EXISTS giveaways (message_id INTEGER PRIMARY KEY, guild_id INTEGER, channel_id INTEGER, prize TEXT, winners_count INTEGER, end_time TEXT, entries TEXT, ended INTEGER DEFAULT 0)''')
        # جدول التذاكر
        await db.execute('''CREATE TABLE IF NOT EXISTS tickets (ticket_id TEXT PRIMARY KEY, guild_id INTEGER, user_id INTEGER, channel_id INTEGER, status TEXT, created_at TEXT, transcript TEXT)''')
        # جدول المتجر
        await db.execute('''CREATE TABLE IF NOT EXISTS shop (item_id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER, item_name TEXT, role_id INTEGER, price INTEGER, description TEXT)''')
        # جدول التحذيرات
        await db.execute('''CREATE TABLE IF NOT EXISTS warnings (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, guild_id INTEGER, moderator_id INTEGER, reason TEXT, timestamp TEXT)''')
        # جدول إعدادات المستويات
        await db.execute('''CREATE TABLE IF NOT EXISTS level_settings (guild_id INTEGER PRIMARY KEY, announce_channel_id INTEGER, announce_enabled INTEGER DEFAULT 1)''')
        # جدول إعدادات الترحيب
        await db.execute('''CREATE TABLE IF NOT EXISTS welcome_settings (guild_id INTEGER PRIMARY KEY, channel_id INTEGER, welcome_enabled INTEGER DEFAULT 1, farewell_enabled INTEGER DEFAULT 1)''')
        # جدول إعدادات الحماية
        await db.execute('''CREATE TABLE IF NOT EXISTS antinuke_settings (guild_id INTEGER PRIMARY KEY, enabled INTEGER DEFAULT 0, log_channel_id INTEGER)''')
        # جدول النسخ الاحتياطية
        await db.execute('''CREATE TABLE IF NOT EXISTS server_backups (id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER, backup_data TEXT, created_at TEXT)''')
        await db.commit()
    logger.info("✅ قاعدة البيانات جاهزة")

# ========== نظام الترخيص ==========
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
        key = secrets.token_hex(16).upper()
        self.licenses["licenses"][key] = {"guild_id": guild_id, "guild_name": guild_name, "activated": False, "expires": (datetime.now().timestamp() + 365 * 24 * 3600)}
        self.save_licenses()
        return key
    def activate(self, key: str, guild_id: int):
        if key not in self.licenses["licenses"]: return False
        lic = self.licenses["licenses"][key]
        if lic["guild_id"] != guild_id: return False
        if lic["expires"] < datetime.now().timestamp(): return False
        lic["activated"] = True
        self.save_licenses()
        return True
    def check(self, guild_id: int):
        if guild_id == OWNER_GUILD_ID: return True
        for key, data in self.licenses["licenses"].items():
            if data["guild_id"] == guild_id and data["activated"] and data["expires"] >= datetime.now().timestamp():
                return True
        return False

license_manager = SimpleLicense()

# ========== البوت الرئيسي ==========
class RTGUltimateBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents, help_command=None)
        self.start_time = datetime.now()
        self.version = "5.0.0"
    async def setup_hook(self):
        logger.info("🔄 جاري التحميل...")
        await init_db()
        if PROTECTION_MODE == 1:
            for guild in self.guilds:
                if not license_manager.check(guild.id):
                    await guild.leave()
        await self.tree.sync()
        logger.info(f"✅ {self.user} جاهز!")
    async def on_guild_join(self, guild: discord.Guild):
        if PROTECTION_MODE == 1 and not license_manager.check(guild.id):
            channel = guild.system_channel or guild.text_channels[0]
            if channel:
                await channel.send("🔒 هذا السيرفر غير مرخص! استخدم `/activate` للتفعيل")
            await asyncio.sleep(60)
            if not license_manager.check(guild.id):
                await guild.leave()

bot = RTGUltimateBot()

# ========== أوامر الترخيص ==========
@bot.tree.command(name="activate", description="تفعيل البوت")
async def activate_cmd(interaction: discord.Interaction, key: str):
    if license_manager.activate(key, interaction.guild_id):
        await interaction.response.send_message("✅ تم تفعيل البوت بنجاح!")
    else:
        await interaction.response.send_message("❌ مفتاح غير صالح!", ephemeral=True)

@bot.tree.command(name="license_info", description="معلومات الترخيص")
async def license_info(interaction: discord.Interaction):
    status = "✅ مفعل" if license_manager.check(interaction.guild_id) else "❌ غير مفعل"
    await interaction.response.send_message(f"🔑 **حالة الترخيص:** {status}", ephemeral=True)

# ========== أمر بناء السيرفر ==========
@bot.tree.command(name="build_server", description="[ADMIN] بناء السيرفر تلقائياً")
@app_commands.default_permissions(administrator=True)
async def build_server(interaction: discord.Interaction):
    await interaction.response.defer()
    guild = interaction.guild
    try:
        # إنشاء الرتب
        roles = {}
        for name, color in [("👑 Owner", 0x000000), ("💎 VIP", 0xFFD700), ("🛡️ Admin", 0xFF0000), ("👥 Member", 0x00FF00)]:
            r = await guild.create_role(name=name, color=discord.Color(color))
            roles[name] = r
        # إنشاء الفئات
        cat_general = await guild.create_category("📁 GENERAL")
        cat_community = await guild.create_category("🎮 COMMUNITY")
        # إنشاء القنوات
        await guild.create_text_channel("welcome", category=cat_general)
        await guild.create_text_channel("rules", category=cat_general)
        await guild.create_text_channel("general-chat", category=cat_community)
        await guild.create_voice_channel("voice-chat", category=cat_community)
        # لوحة التحقق
        welcome_ch = guild.get_channel(discord.utils.get(guild.text_channels, name="welcome").id)
        if welcome_ch:
            class VerifyView(discord.ui.View):
                @discord.ui.button(label="✅ تحقق", style=discord.ButtonStyle.success)
                async def verify(self, ctx: discord.Interaction, btn: discord.ui.Button):
                    member_role = discord.utils.get(guild.roles, name="👥 Member")
                    if member_role:
                        await ctx.user.add_roles(member_role)
                        await ctx.response.send_message("✅ تم التحقق!", ephemeral=True)
            await welcome_ch.send("🔐 اضغط للتحقق", view=VerifyView())
        await interaction.followup.send("✅ تم بناء السيرفر بنجاح!")
    except Exception as e:
        await interaction.followup.send(f"❌ خطأ: {e}")

# ========== لوحة التحكم ==========
@bot.tree.command(name="dashboard", description="لوحة التحكم الرئيسية")
async def dashboard(interaction: discord.Interaction):
    embed = discord.Embed(title="🎮 لوحة تحكم RTG Bot", color=discord.Color.purple())
    embed.add_field(name="💰 الاقتصاد", value="`/balance`, `/work`, `/shop`", inline=True)
    embed.add_field(name="📈 المستويات", value="`/rank`, `/leaderboard`", inline=True)
    embed.add_field(name="🛡️ الإدارة", value="`/clear`, `/ban`, `/kick`", inline=True)
    embed.add_field(name="🎫 التذاكر", value="`/ticket_panel`, `/ticket_close`", inline=True)
    embed.add_field(name="🎁 السحوبات", value="`/giveaway_create`", inline=True)
    embed.add_field(name="🏗️ البناء", value="`/build_server`", inline=True)
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ========== أوامر الاقتصاد الأساسية ==========
@bot.tree.command(name="balance", description="عرض رصيدك")
async def balance(interaction: discord.Interaction):
    async with aiosqlite.connect("data/rtg_bot.db") as db:
        async with db.execute("SELECT balance FROM economy WHERE user_id = ? AND guild_id = ?", (interaction.user.id, interaction.guild_id)) as cur:
            res = await cur.fetchone()
            bal = res[0] if res else 0
    await interaction.response.send_message(f"💰 رصيدك: **{bal}** عملة")

@bot.tree.command(name="daily", description="مكافأة يومية")
async def daily(interaction: discord.Interaction):
    async with aiosqlite.connect("data/rtg_bot.db") as db:
        await db.execute('''INSERT INTO economy (user_id, guild_id, balance) VALUES (?, ?, 100) ON CONFLICT(user_id, guild_id) DO UPDATE SET balance = balance + 100''', (interaction.user.id, interaction.guild_id))
        await db.commit()
    await interaction.response.send_message("🎁 حصلت على 100 عملة!")

@bot.tree.command(name="work", description="اعمل لكسب المال")
async def work(interaction: discord.Interaction):
    import random
    earnings = random.randint(50, 150)
    async with aiosqlite.connect("data/rtg_bot.db") as db:
        await db.execute('''INSERT INTO economy (user_id, guild_id, balance) VALUES (?, ?, ?) ON CONFLICT(user_id, guild_id) DO UPDATE SET balance = balance + ?''', (interaction.user.id, interaction.guild_id, earnings, earnings))
        await db.commit()
    await interaction.response.send_message(f"💼 عملت وكسبت **{earnings}** عملة!")

@bot.tree.command(name="pay", description="تحويل عملات")
async def pay(interaction: discord.Interaction, member: discord.Member, amount: int):
    async with aiosqlite.connect("data/rtg_bot.db") as db:
        async with db.execute("SELECT balance FROM economy WHERE user_id = ? AND guild_id = ?", (interaction.user.id, interaction.guild_id)) as cur:
            bal = (await cur.fetchone() or [0])[0]
        if bal < amount:
            await interaction.response.send_message("❌ رصيدك غير كافٍ!")
            return
        await db.execute("UPDATE economy SET balance = balance - ? WHERE user_id = ? AND guild_id = ?", (amount, interaction.user.id, interaction.guild_id))
        await db.execute("UPDATE economy SET balance = balance + ? WHERE user_id = ? AND guild_id = ?", (amount, member.id, interaction.guild_id))
        await db.commit()
    await interaction.response.send_message(f"✅ حولت **{amount}** عملة إلى {member.mention}")

@bot.tree.command(name="shop", description="عرض المتجر")
async def shop(interaction: discord.Interaction):
    embed = discord.Embed(title="🛒 المتجر", color=discord.Color.purple())
    embed.add_field(name="👑 رتبة VIP", value="5000 عملة", inline=True)
    embed.add_field(name="🎨 لون مخصص", value="2000 عملة", inline=True)
    await interaction.response.send_message(embed=embed)

# ========== أمر المستويات ==========
@bot.tree.command(name="rank", description="عرض رتبتك")
async def rank(interaction: discord.Interaction, member: discord.Member = None):
    target = member or interaction.user
    async with aiosqlite.connect("data/rtg_bot.db") as db:
        async with db.execute("SELECT level, xp FROM leveling WHERE user_id = ? AND guild_id = ?", (target.id, interaction.guild_id)) as cur:
            res = await cur.fetchone()
    level, xp = res if res else (0, 0)
    embed = discord.Embed(title=f"📊 رتبة {target.display_name}", color=discord.Color.blue())
    embed.add_field(name="🏆 المستوى", value=level, inline=True)
    embed.add_field(name="✨ الخبرة", value=xp, inline=True)
    await interaction.response.send_message(embed=embed)

# ========== أوامر الموسيقى ==========
@bot.tree.command(name="play", description="تشغيل أغنية")
async def play(interaction: discord.Interaction, query: str):
    if not interaction.user.voice:
        await interaction.response.send_message("❌ يجب أن تكون في قناة صوتية!")
        return
    await interaction.response.send_message(f"🎵 جاري تشغيل: {query}")

@bot.tree.command(name="skip", description="تخطي الأغنية")
async def skip(interaction: discord.Interaction):
    await interaction.response.send_message("⏭️ تم التخطي")

# ========== أوامر الإدارة ==========
@bot.tree.command(name="clear", description="مسح الرسائل")
@app_commands.default_permissions(manage_messages=True)
async def clear(interaction: discord.Interaction, amount: int):
    if amount <= 0 or amount > 100:
        await interaction.response.send_message("❌ العدد بين 1 و 100")
        return
    await interaction.channel.purge(limit=amount)
    await interaction.response.send_message(f"✅ تم مسح {amount} رسالة", ephemeral=True)

@bot.tree.command(name="ban", description="حظر عضو")
@app_commands.default_permissions(ban_members=True)
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = None):
    await member.ban(reason=reason)
    await interaction.response.send_message(f"🔨 تم حظر {member.mention}")

@bot.tree.command(name="kick", description="طرد عضو")
@app_commands.default_permissions(kick_members=True)
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = None):
    await member.kick(reason=reason)
    await interaction.response.send_message(f"👢 تم طرد {member.mention}")

# ========== لوحة التذاكر ==========
@bot.tree.command(name="ticket_panel", description="[ADMIN] إنشاء لوحة التذاكر")
@app_commands.default_permissions(administrator=True)
async def ticket_panel(interaction: discord.Interaction):
    category = discord.utils.get(interaction.guild.categories, name="🎫 TICKETS")
    if not category:
        category = await interaction.guild.create_category("🎫 TICKETS")
    
    class TicketView(discord.ui.View):
        @discord.ui.button(label="🎫 فتح تذكرة", style=discord.ButtonStyle.primary)
        async def ticket(self, ctx: discord.Interaction, btn: discord.ui.Button):
            ch = await interaction.guild.create_text_channel(f"ticket-{ctx.user.name}", category=category)
            await ch.set_permissions(ctx.user, read_messages=True, send_messages=True)
            await ch.send(f"مرحباً {ctx.user.mention}! كيف يمكننا مساعدتك؟")
            await ctx.response.send_message(f"✅ تم فتح تذكرة: {ch.mention}", ephemeral=True)
    
    embed = discord.Embed(title="🎫 مركز الدعم", description="اضغط للفتح تذكرة", color=discord.Color.blue())
    await interaction.response.send_message(embed=embed, view=TicketView())

@bot.tree.command(name="ticket_close", description="إغلاق التذكرة")
async def ticket_close(interaction: discord.Interaction):
    if not interaction.channel.name.startswith("ticket-"):
        await interaction.response.send_message("❌ هذه ليست تذكرة!", ephemeral=True)
        return
    await interaction.response.send_message("🔒 جاري الإغلاق...")
    await asyncio.sleep(2)
    await interaction.channel.delete()

# ========== السحوبات ==========
@bot.tree.command(name="giveaway_create", description="[ADMIN] إنشاء سحوبات")
@app_commands.default_permissions(administrator=True)
async def giveaway_create(interaction: discord.Interaction, prize: str, duration: str, winners: int = 1):
    seconds = {"m": 60, "h": 3600, "d": 86400}.get(duration[-1], 60) * int(duration[:-1])
    end_time = datetime.now().timestamp() + seconds
    
    embed = discord.Embed(title="🎉 سحوبات!", description=f"**الجائزة:** {prize}\n**الفائزون:** {winners}\nينتهي بعد {duration}", color=discord.Color.purple())
    
    class GiveawayButton(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=None)
            self.entries = []
        @discord.ui.button(label="🎉 شارك!", style=discord.ButtonStyle.success)
        async def enter(self, ctx: discord.Interaction, btn: discord.ui.Button):
            if ctx.user.id not in self.entries:
                self.entries.append(ctx.user.id)
                await ctx.response.send_message("✅ تم تسجيل مشاركتك!", ephemeral=True)
    
    view = GiveawayButton()
    await interaction.response.send_message(embed=embed, view=view)
    
    await asyncio.sleep(seconds)
    if view.entries:
        import random
        winners_list = random.sample(view.entries, min(winners, len(view.entries)))
        winner_mentions = ", ".join([f"<@{w}>" for w in winners_list])
        await interaction.channel.send(f"🎉 فاز بـ **{prize}**: {winner_mentions}")
    else:
        await interaction.channel.send(f"❌ لا مشاركين في سحوبات {prize}")

# ========== حدث الرسائل للمستويات ==========
@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return
    async with aiosqlite.connect("data/rtg_bot.db") as db:
        await db.execute('''INSERT INTO leveling (user_id, guild_id, xp, level) VALUES (?, ?, 15, 0) ON CONFLICT(user_id, guild_id) DO UPDATE SET xp = xp + 15''', (message.author.id, message.guild.id))
        await db.commit()
    await bot.process_commands(message)

# ========== حدث الترحيب ==========
@bot.event
async def on_member_join(member):
    async with aiosqlite.connect("data/rtg_bot.db") as db:
        async with db.execute("SELECT channel_id FROM welcome_settings WHERE guild_id = ?", (member.guild.id,)) as cur:
            res = await cur.fetchone()
    if res:
        channel = member.guild.get_channel(res[0])
        if channel:
            await channel.send(f"👋 مرحباً {member.mention} في {member.guild.name}!")

# ========== حدث المغادرة ==========
@bot.event
async def on_member_remove(member):
    async with aiosqlite.connect("data/rtg_bot.db") as db:
        async with db.execute("SELECT channel_id FROM welcome_settings WHERE guild_id = ?", (member.guild.id,)) as cur:
            res = await cur.fetchone()
    if res:
        channel = member.guild.get_channel(res[0])
        if channel:
            await channel.send(f"😢 وداعاً {member.name}!")

# ========== أوامر ترفيهية ==========
@bot.tree.command(name="hug", description="احتضن عضوًا")
async def hug(interaction: discord.Interaction, member: discord.Member):
    await interaction.response.send_message(f"🤗 {interaction.user.mention} يحتضن {member.mention}!")

@bot.tree.command(name="serverinfo", description="معلومات السيرفر")
async def serverinfo(interaction: discord.Interaction):
    guild = interaction.guild
    embed = discord.Embed(title=f"📊 {guild.name}", color=discord.Color.blue())
    embed.add_field(name="👑 المالك", value=guild.owner.mention, inline=True)
    embed.add_field(name="👥 الأعضاء", value=guild.member_count, inline=True)
    embed.add_field(name="💬 القنوات", value=len(guild.channels), inline=True)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="avatar", description="عرض الصورة")
async def avatar(interaction: discord.Interaction, member: discord.Member = None):
    target = member or interaction.user
    embed = discord.Embed(title=f"🖼️ {target.display_name}", color=discord.Color.blue())
    embed.set_image(url=target.display_avatar.url)
    await interaction.response.send_message(embed=embed)

# ========== أمر المساعدة ==========
@bot.tree.command(name="help", description="عرض المساعدة")
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(title="🎮 RTG Ultimate Bot", color=discord.Color.purple())
    embed.add_field(name="💰 الاقتصاد", value="`/balance`, `/daily`, `/work`, `/pay`, `/shop`", inline=False)
    embed.add_field(name="📈 المستويات", value="`/rank`", inline=False)
    embed.add_field(name="🎵 الموسيقى", value="`/play`, `/skip`", inline=False)
    embed.add_field(name="🛡️ الإدارة", value="`/clear`, `/ban`, `/kick`", inline=False)
    embed.add_field(name="🎫 التذاكر", value="`/ticket_panel`, `/ticket_close`", inline=False)
    embed.add_field(name="🎁 السحوبات", value="`/giveaway_create`", inline=False)
    embed.add_field(name="🏗️ بناء السيرفر", value="`/build_server`", inline=False)
    embed.add_field(name="🎭 الترفيه", value="`/hug`, `/serverinfo`, `/avatar`", inline=False)
    embed.set_footer(text=f"البوت على {len(bot.guilds)} سيرفر")
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ========== تشغيل البوت ==========
if __name__ == "__main__":
    if not TOKEN or TOKEN == "ضع_توكن_البوت_هنا":
        print("❌ خطأ: لم يتم إدخال توكن البوت!")
    else:
        bot.run(TOKEN)
