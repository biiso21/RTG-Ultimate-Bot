import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import os
import json
import threading
import aiosqlite
import secrets
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, jsonify

load_dotenv()

print("🚀 بدء تشغيل البوت...")

# ========== إنشاء المجلدات ==========
for folder in ["data", "data/backups"]:
    os.makedirs(folder, exist_ok=True)

# ========== إعداد Flask (API فقط) ==========
app = Flask(__name__)

@app.route('/')
def home():
    return """
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>RTG Ultimate Bot</title>
        <style>
            body { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; font-family: Arial, sans-serif; color: white; text-align: center; padding: 50px; }
            .card { background: rgba(255,255,255,0.1); border-radius: 20px; padding: 30px; margin: 20px auto; max-width: 600px; backdrop-filter: blur(10px); }
            h1 { font-size: 3rem; }
            .btn { background: #5865F2; color: white; padding: 12px 30px; border-radius: 30px; text-decoration: none; display: inline-block; margin: 10px; }
            .stats { display: flex; justify-content: center; gap: 20px; margin-top: 30px; }
            .stat { background: rgba(0,0,0,0.3); border-radius: 15px; padding: 15px; min-width: 120px; }
            .stat-number { font-size: 2rem; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="card">
            <h1>🎮 RTG Ultimate Bot</h1>
            <p>أفضل بوت متكامل لإدارة سيرفرات ديسكورد</p>
            <div class="stats">
                <div class="stat">
                    <div class="stat-number" id="guilds">...</div>
                    <div>سيرفرات</div>
                </div>
                <div class="stat">
                    <div class="stat-number" id="users">...</div>
                    <div>مستخدمين</div>
                </div>
                <div class="stat">
                    <div class="stat-number" id="uptime">...</div>
                    <div>وقت التشغيل</div>
                </div>
            </div>
            <div>
                <a href="https://discord.com/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=8&scope=bot%20applications.commands" class="btn">➕ إضافة البوت</a>
                <a href="/dashboard" class="btn">📊 لوحة التحكم</a>
            </div>
        </div>
        <script>
            fetch('/api/stats').then(r=>r.json()).then(d=>{
                document.getElementById('guilds').innerText = d.guilds;
                document.getElementById('users').innerText = d.users;
                document.getElementById('uptime').innerText = d.uptime;
            });
        </script>
    </body>
    </html>
    """

@app.route('/dashboard')
def dashboard():
    return """
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>لوحة التحكم - RTG Bot</title>
        <style>
            body { background: #f5f5f5; font-family: Arial, sans-serif; margin: 0; padding: 0; }
            .sidebar { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); width: 250px; height: 100vh; position: fixed; color: white; padding: 20px; }
            .sidebar a { color: white; text-decoration: none; display: block; padding: 12px; margin: 5px 0; border-radius: 10px; }
            .sidebar a:hover { background: rgba(255,255,255,0.2); }
            .content { margin-right: 250px; padding: 20px; }
            .card { background: white; border-radius: 15px; padding: 20px; margin-bottom: 20px; box-shadow: 0 5px 15px rgba(0,0,0,0.1); }
            .server-item { cursor: pointer; padding: 10px; border-bottom: 1px solid #eee; }
            .server-item:hover { background: #f0f0f0; }
            .stat-card { display: inline-block; background: white; border-radius: 15px; padding: 20px; margin: 10px; min-width: 150px; text-align: center; }
            .stat-number { font-size: 2rem; font-weight: bold; color: #667eea; }
        </style>
    </head>
    <body>
        <div class="sidebar">
            <h3>🤖 RTG Bot</h3>
            <hr>
            <a href="/dashboard">📊 لوحة التحكم</a>
            <a href="/economy">💰 الاقتصاد</a>
            <a href="/leveling">📈 المستويات</a>
            <a href="/moderation">🛡️ الإدارة</a>
            <a href="/">🏠 الرئيسية</a>
        </div>
        <div class="content">
            <h2>📊 لوحة التحكم</h2>
            <div id="stats-container"></div>
            <div class="card">
                <h3>🌐 السيرفرات</h3>
                <div id="servers-list">جاري التحميل...</div>
            </div>
            <div class="card" id="server-details" style="display:none;">
                <h3>📈 تفاصيل السيرفر</h3>
                <div id="economy-leaderboard"></div>
                <div id="level-leaderboard"></div>
            </div>
        </div>
        <script>
            fetch('/api/stats').then(r=>r.json()).then(d=>{
                let html = `<div class="stat-card"><div class="stat-number">${d.guilds}</div><div>سيرفرات</div></div>
                           <div class="stat-card"><div class="stat-number">${d.users}</div><div>مستخدمين</div></div>
                           <div class="stat-card"><div class="stat-number">${d.uptime}</div><div>وقت التشغيل</div></div>`;
                document.getElementById('stats-container').innerHTML = html;
            });
            fetch('/api/guilds').then(r=>r.json()).then(data=>{
                let html = '';
                data.forEach(g=>{ html += `<div class="server-item" onclick="loadServer(${g.id})">📡 ${g.name} (${g.members} عضو)</div>`; });
                document.getElementById('servers-list').innerHTML = html;
            });
            function loadServer(id){
                document.getElementById('server-details').style.display = 'block';
                fetch(`/api/economy/${id}`).then(r=>r.json()).then(data=>{
                    let html = '<h4>💰 قائمة الأغنياء</h4><ol>';
                    data.forEach(u=>{ html += `<li>${u.name} - ${u.balance} عملة</li>`; });
                    html += '</ol>';
                    document.getElementById('economy-leaderboard').innerHTML = html;
                });
                fetch(`/api/leveling/${id}`).then(r=>r.json()).then(data=>{
                    let html = '<h4>🏆 أعلى المستويات</h4><ol>';
                    data.forEach(u=>{ html += `<li>${u.name} - المستوى ${u.level} (${u.xp} XP)</li>`; });
                    html += '</ol>';
                    document.getElementById('level-leaderboard').innerHTML = html;
                });
            }
        </script>
    </body>
    </html>
    """

@app.route('/api/stats')
def api_stats():
    return jsonify({
        'guilds': len(bot.guilds),
        'users': sum(g.member_count for g in bot.guilds),
        'uptime': str(datetime.now() - bot.start_time).split('.')[0]
    })

@app.route('/api/guilds')
def api_guilds():
    return jsonify([{'id': g.id, 'name': g.name, 'members': g.member_count} for g in bot.guilds])

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

@app.route('/economy')
def economy_page():
    return "<h2>💰 نظام الاقتصاد</h2><p>استخدم الأوامر التالية:</p><ul><li>/balance - عرض رصيدك</li><li>/daily - مكافأة يومية</li><li>/work - العمل لكسب المال</li><li>/pay - تحويل عملات</li><li>/shop - عرض المتجر</li></ul><a href='/dashboard'>🔙 العودة</a>"

@app.route('/leveling')
def leveling_page():
    return "<h2>📈 نظام المستويات</h2><p>استخدم الأوامر التالية:</p><ul><li>/rank - عرض رتبتك</li><li>/rank @user - عرض رتبة عضو</li></ul><a href='/dashboard'>🔙 العودة</a>"

@app.route('/moderation')
def moderation_page():
    return "<h2>🛡️ نظام الإدارة</h2><p>استخدم الأوامر التالية:</p><ul><li>/clear - مسح الرسائل</li><li>/ban - حظر عضو</li><li>/kick - طرد عضو</li><li>/build_server - بناء السيرفر</li><li>/nuke_server - حذف جميع القنوات والرتب</li></ul><a href='/dashboard'>🔙 العودة</a>"

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
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="RTG Community | /help"))

bot = RTGUltimateBot()

# ========== أمر حذف القنوات والرتب ==========
@bot.tree.command(name="nuke_server", description="[OWNER] حذف جميع القنوات والرتب")
async def nuke_server(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("❌ هذا الأمر للمطور فقط!", ephemeral=True)
        return
    
    await interaction.response.send_message("⚠️ جاري حذف جميع القنوات والرتب...", ephemeral=True)
    guild = interaction.guild
    
    for channel in guild.channels:
        try: await channel.delete()
        except: pass
    
    for role in guild.roles:
        if role.name != "@everyone":
            try: await role.delete()
            except: pass
    
    await interaction.followup.send("✅ تم حذف جميع القنوات والرتب!", ephemeral=True)

# ========== أمر بناء السيرفر ==========
@bot.tree.command(name="build_server", description="[ADMIN] بناء السيرفر تلقائياً")
@app_commands.default_permissions(administrator=True)
async def build_server(interaction: discord.Interaction):
    await interaction.response.defer()
    guild = interaction.guild
    try:
        for name, color in [("👑 Owner", 0x000000), ("💎 VIP", 0xFFD700), ("🛡️ Admin", 0xFF0000), ("👥 Member", 0x00FF00)]:
            await guild.create_role(name=name, color=discord.Color(color))
        
        cat_general = await guild.create_category("📁 GENERAL")
        cat_community = await guild.create_category("🎮 COMMUNITY")
        
        await guild.create_text_channel("welcome", category=cat_general)
        await guild.create_text_channel("rules", category=cat_general)
        await guild.create_text_channel("general-chat", category=cat_community)
        await guild.create_voice_channel("voice-chat", category=cat_community)
        
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
    await interaction.response.send_message(embed=embed)

# ========== أمر المستويات ==========
@bot.tree.command(name="rank", description="عرض رتبتك")
async def rank(interaction: discord.Interaction, member: discord.Member = None):
    target = member or interaction.user
    async with aiosqlite.connect("data/rtg_bot.db") as db:
        async with db.execute("SELECT level, xp FROM leveling WHERE user_id = ? AND guild_id = ?", (target.id, interaction.guild_id)) as cur:
            res = await cur.fetchone()
    level, xp = res if res else (0, 0)
    await interaction.response.send_message(f"📊 **{target.display_name}**\n🏆 المستوى: {level}\n✨ الخبرة: {xp}")

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

# ========== حدث الرسائل ==========
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

# ========== أوامر ترفيهية ==========
@bot.tree.command(name="hug", description="احتضن عضوًا")
async def hug(interaction: discord.Interaction, member: discord.Member):
    await interaction.response.send_message(f"🤗 {interaction.user.mention} يحتضن {member.mention}!")

@bot.tree.command(name="serverinfo", description="معلومات السيرفر")
async def serverinfo(interaction: discord.Interaction):
    guild = interaction.guild
    await interaction.response.send_message(f"📊 **{guild.name}**\n👑 المالك: {guild.owner.mention}\n👥 الأعضاء: {guild.member_count}\n💬 القنوات: {len(guild.channels)}")

@bot.tree.command(name="help", description="عرض المساعدة")
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(title="🎮 RTG Ultimate Bot", color=discord.Color.purple())
    embed.add_field(name="💰 الاقتصاد", value="`/balance`, `/daily`, `/work`, `/pay`, `/shop`", inline=False)
    embed.add_field(name="📈 المستويات", value="`/rank`", inline=False)
    embed.add_field(name="🛡️ الإدارة", value="`/clear`, `/ban`, `/kick`, `/build_server`, `/nuke_server`", inline=False)
    embed.add_field(name="🎭 الترفيه", value="`/hug`, `/serverinfo`", inline=False)
    embed.add_field(name="🌐 الويب", value="https://rtg-ultimate-bot.onrender.com", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ========== تشغيل البوت ==========
if __name__ == "__main__":
    if not TOKEN:
        print("❌ خطأ: لم يتم إدخال توكن البوت!")
    else:
        bot.run(TOKEN)
