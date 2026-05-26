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
import traceback
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, render_template, jsonify, request, redirect, url_for, session

load_dotenv()

print("🚀 بدء تشغيل البوت...")

# ========== إنشاء المجلدات ==========
for folder in ["data", "data/backups", "logs", "templates", "static"]:
    os.makedirs(folder, exist_ok=True)

# ========== إعداد Flask ==========
app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

# ========== صفحات الويب ==========
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/economy')
def economy_page():
    return render_template('economy.html')

@app.route('/leveling')
def leveling_page():
    return render_template('leveling.html')

@app.route('/moderation')
def moderation_page():
    return render_template('moderation.html')

@app.route('/tickets')
def tickets_page():
    return render_template('tickets.html')

@app.route('/giveaways')
def giveaways_page():
    return render_template('giveaways.html')

@app.route('/settings')
def settings_page():
    return render_template('settings.html')

# ========== API Routes ==========
@app.route('/api/stats')
def api_stats():
    return jsonify({
        'guilds': len(bot.guilds),
        'users': sum(g.member_count for g in bot.guilds),
        'uptime': str(datetime.now() - bot.start_time).split('.')[0]
    })

@app.route('/api/guilds')
def api_guilds():
    guilds_data = []
    for guild in bot.guilds:
        guilds_data.append({
            'id': guild.id,
            'name': guild.name,
            'icon': str(guild.icon.url) if guild.icon else None,
            'members': guild.member_count
        })
    return jsonify(guilds_data)

@app.route('/api/economy/<int:guild_id>')
async def api_economy(guild_id):
    async with aiosqlite.connect("data/rtg_bot.db") as db:
        async with db.execute("SELECT user_id, balance FROM economy WHERE guild_id = ? ORDER BY balance DESC LIMIT 10", (guild_id,)) as cur:
            rows = await cur.fetchall()
    data = []
    for user_id, balance in rows:
        guild = bot.get_guild(guild_id)
        user = guild.get_member(user_id) if guild else None
        data.append({'name': user.name if user else str(user_id), 'balance': balance})
    return jsonify(data)

@app.route('/api/leveling/<int:guild_id>')
async def api_leveling(guild_id):
    async with aiosqlite.connect("data/rtg_bot.db") as db:
        async with db.execute("SELECT user_id, level, xp FROM leveling WHERE guild_id = ? ORDER BY level DESC LIMIT 10", (guild_id,)) as cur:
            rows = await cur.fetchall()
    data = []
    for user_id, level, xp in rows:
        guild = bot.get_guild(guild_id)
        user = guild.get_member(user_id) if guild else None
        data.append({'name': user.name if user else str(user_id), 'level': level, 'xp': xp})
    return jsonify(data)

def run_web():
    app.run(host='0.0.0.0', port=8080)

threading.Thread(target=run_web, daemon=True).start()
print("✅ خادم الويب يعمل على المنفذ 8080")

# ========== إعدادات البوت ==========
intents = discord.Intents.all()
intents.message_content = True
intents.members = True
intents.voice_states = True

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "1276968112071249958"))
OWNER_GUILD_ID = int(os.getenv("OWNER_GUILD_ID", "1361756331404693665"))

print(f"✅ TOKEN موجود: {bool(TOKEN)}")

# ========== تهيئة قاعدة البيانات ==========
async def init_db():
    async with aiosqlite.connect("data/rtg_bot.db") as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS leveling (user_id INTEGER, guild_id INTEGER, xp INTEGER DEFAULT 0, level INTEGER DEFAULT 0, total_messages INTEGER DEFAULT 0, PRIMARY KEY (user_id, guild_id))''')
        await db.execute('''CREATE TABLE IF NOT EXISTS economy (user_id INTEGER, guild_id INTEGER, balance INTEGER DEFAULT 0, daily_streak INTEGER DEFAULT 0, last_daily TEXT, PRIMARY KEY (user_id, guild_id))''')
        await db.execute('''CREATE TABLE IF NOT EXISTS giveaways (message_id INTEGER PRIMARY KEY, guild_id INTEGER, channel_id INTEGER, prize TEXT, winners_count INTEGER, end_time TEXT, entries TEXT, ended INTEGER DEFAULT 0)''')
        await db.execute('''CREATE TABLE IF NOT EXISTS tickets (ticket_id TEXT PRIMARY KEY, guild_id INTEGER, user_id INTEGER, channel_id INTEGER, status TEXT, created_at TEXT)''')
        await db.execute('''CREATE TABLE IF NOT EXISTS warnings (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, guild_id INTEGER, moderator_id INTEGER, reason TEXT, timestamp TEXT)''')
        await db.execute('''CREATE TABLE IF NOT EXISTS welcome_settings (guild_id INTEGER PRIMARY KEY, channel_id INTEGER, welcome_enabled INTEGER DEFAULT 1)''')
        await db.commit()
    print("✅ قاعدة البيانات جاهزة")

# ========== البوت الرئيسي ==========
class RTGUltimateBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents, help_command=None)
        self.start_time = datetime.now()
        self.version = "5.0.0"
    
    async def setup_hook(self):
        print("🔄 جاري تحميل البوت...")
        await init_db()
        await self.tree.sync()
        print("✅ تم مزامنة الأوامر")
    
    async def on_ready(self):
        print(f"✅ {self.user} متصل!")
        print(f"📊 موجود في {len(self.guilds)} سيرفر")
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="RTG Community"))

bot = RTGUltimateBot()

# ========== أمر حذف القنوات والرتب ==========
@bot.tree.command(name="nuke_server", description="[OWNER] حذف جميع القنوات والرتب في السيرفر")
@app_commands.default_permissions(administrator=True)
async def nuke_server(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("❌ هذا الأمر للمطور فقط!", ephemeral=True)
        return
    
    await interaction.response.send_message("⚠️ جاري حذف جميع القنوات والرتب...", ephemeral=True)
    guild = interaction.guild
    
    # حذف جميع القنوات
    for channel in guild.channels:
        try:
            await channel.delete()
        except:
            pass
    
    # حذف جميع الرتب (ما عدا @everyone)
    for role in guild.roles:
        if role.name != "@everyone":
            try:
                await role.delete()
            except:
                pass
    
    await interaction.followup.send("✅ تم حذف جميع القنوات والرتب!", ephemeral=True)

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
        await guild.create_text_channel("announcements", category=cat_general)
        await guild.create_text_channel("general-chat", category=cat_community)
        await guild.create_text_channel("bot-commands", category=cat_community)
        await guild.create_voice_channel("voice-chat", category=cat_community)
        
        # لوحة التحقق
        welcome_ch = discord.utils.get(guild.text_channels, name="welcome")
        if welcome_ch:
            class VerifyView(discord.ui.View):
                @discord.ui.button(label="✅ تحقق", style=discord.ButtonStyle.success)
                async def verify(self, ctx: discord.Interaction, btn: discord.ui.Button):
                    member_role = discord.utils.get(guild.roles, name="👥 Member")
                    if member_role:
                        await ctx.user.add_roles(member_role)
                        await ctx.response.send_message("✅ تم التحقق! مرحباً بك في السيرفر", ephemeral=True)
            await welcome_ch.send("🔐 **التحقق من الدخول**\nاضغط على الزر أدناه للتحقق والوصول إلى السيرفر", view=VerifyView())
        
        await interaction.followup.send("✅ تم بناء السيرفر بنجاح!")
    except Exception as e:
        await interaction.followup.send(f"❌ خطأ: {e}")

# ========== أوامر الاقتصاد ==========
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
    embed.add_field(name="📢 إعلان", value="10000 عملة", inline=True)
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
    try:
        seconds = {"m": 60, "h": 3600, "d": 86400}.get(duration[-1], 60) * int(duration[:-1])
    except:
        await interaction.response.send_message("❌ صيغة غير صحيحة! استخدم: 30m, 1h, 2d", ephemeral=True)
        return
    
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
    try:
        async with aiosqlite.connect("data/rtg_bot.db") as db:
            await db.execute('''INSERT INTO leveling (user_id, guild_id, xp, level) VALUES (?, ?, 15, 0) ON CONFLICT(user_id, guild_id) DO UPDATE SET xp = xp + 15''', (message.author.id, message.guild.id))
            await db.commit()
    except:
        pass
    await bot.process_commands(message)

# ========== حدث الترحيب ==========
@bot.event
async def on_member_join(member):
    try:
        async with aiosqlite.connect("data/rtg_bot.db") as db:
            async with db.execute("SELECT channel_id FROM welcome_settings WHERE guild_id = ?", (member.guild.id,)) as cur:
                res = await cur.fetchone()
        if res:
            channel = member.guild.get_channel(res[0])
            if channel:
                await channel.send(f"👋 مرحباً {member.mention} في {member.guild.name}!")
    except:
        pass

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
    embed.add_field(name="🎵 الموسيقى", value="`/play`", inline=False)
    embed.add_field(name="🛡️ الإدارة", value="`/clear`, `/ban`, `/kick`", inline=False)
    embed.add_field(name="🎫 التذاكر", value="`/ticket_panel`, `/ticket_close`", inline=False)
    embed.add_field(name="🎁 السحوبات", value="`/giveaway_create`", inline=False)
    embed.add_field(name="🏗️ البناء", value="`/build_server`", inline=False)
    embed.add_field(name="💣 الحذف", value="`/nuke_server`", inline=False)
    embed.add_field(name="🌐 الويب", value="https://rtg-ultimate-bot.onrender.com", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ========== تشغيل البوت ==========
if __name__ == "__main__":
    if not TOKEN:
        print("❌ خطأ: لم يتم إدخال توكن البوت!")
    else:
        bot.run(TOKEN)
