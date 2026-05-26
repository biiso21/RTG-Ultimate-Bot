import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
import random
from datetime import datetime, timedelta

class EconomySystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.work_cooldowns = {}
    
    async def cog_load(self):
        async with aiosqlite.connect("data/rtg_bot.db") as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS economy (
                    user_id INTEGER,
                    guild_id INTEGER,
                    balance INTEGER DEFAULT 0,
                    bank INTEGER DEFAULT 0,
                    daily_streak INTEGER DEFAULT 0,
                    last_daily TEXT,
                    job TEXT DEFAULT '🍔 Burger Flipper',
                    job_level INTEGER DEFAULT 1,
                    PRIMARY KEY (user_id, guild_id)
                )
            ''')
            await db.execute('''
                CREATE TABLE IF NOT EXISTS shop (
                    item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER,
                    item_name TEXT,
                    item_type TEXT,
                    role_id INTEGER,
                    price INTEGER,
                    description TEXT
                )
            ''')
            await db.commit()
    
    async def get_balance(self, user_id: int, guild_id: int) -> int:
        async with aiosqlite.connect("data/rtg_bot.db") as db:
            async with db.execute("SELECT balance FROM economy WHERE user_id = ? AND guild_id = ?", (user_id, guild_id)) as cursor:
                result = await cursor.fetchone()
                return result[0] if result else 0
    
    async def add_balance(self, user_id: int, guild_id: int, amount: int):
        async with aiosqlite.connect("data/rtg_bot.db") as db:
            await db.execute('''
                INSERT INTO economy (user_id, guild_id, balance) VALUES (?, ?, ?)
                ON CONFLICT(user_id, guild_id) DO UPDATE SET balance = balance + ?
            ''', (user_id, guild_id, amount, amount))
            await db.commit()
    
    JOBS = {
        "🍔 Burger Flipper": {"salary": (50, 100), "multiplier": 5},
        "💻 Programmer": {"salary": (150, 250), "multiplier": 15},
        "🎵 Musician": {"salary": (80, 150), "multiplier": 8},
        "🛡️ Security": {"salary": (100, 180), "multiplier": 10},
        "👑 Streamer": {"salary": (200, 400), "multiplier": 20},
        "📚 Teacher": {"salary": (120, 200), "multiplier": 12},
        "⚕️ Doctor": {"salary": (180, 300), "multiplier": 18},
    }
    
    # ========== الأوامر ==========
    
    @app_commands.command(name="balance", description="عرض رصيدك")
    async def balance(self, interaction: discord.Interaction, member: discord.Member = None):
        target = member or interaction.user
        balance = await self.get_balance(target.id, interaction.guild_id)
        
        embed = discord.Embed(title=f"💰 رصيد {target.display_name}", description=f"**{balance}** عملة", color=discord.Color.gold())
        embed.set_thumbnail(url=target.display_avatar.url)
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="daily", description="مكافأة يومية")
    async def daily(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        guild_id = interaction.guild_id
        today = datetime.now().date()
        
        async with aiosqlite.connect("data/rtg_bot.db") as db:
            async with db.execute("SELECT daily_streak, last_daily FROM economy WHERE user_id = ? AND guild_id = ?", (user_id, guild_id)) as cursor:
                result = await cursor.fetchone()
            
            if result and result[1]:
                last_date = datetime.fromisoformat(result[1]).date()
                if last_date == today:
                    await interaction.response.send_message("❌ لقد حصلت على مكافأتك اليوم بالفعل!")
                    return
                streak = result[0] + 1 if last_date == today - timedelta(days=1) else 1
            else:
                streak = 1
            
            reward = 100 + (streak * 10)
            
            await db.execute('''
                INSERT INTO economy (user_id, guild_id, balance, daily_streak, last_daily)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id, guild_id) DO UPDATE SET
                    balance = balance + ?,
                    daily_streak = ?,
                    last_daily = ?
            ''', (user_id, guild_id, reward, streak, today.isoformat(), reward, streak, today.isoformat()))
            await db.commit()
        
        embed = discord.Embed(title="🎁 مكافأة يومية!", description=f"{interaction.user.mention} حصلت على **{reward}** عملة!\n🔥 السلسلة: {streak} يوم", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="pay", description="تحويل عملات")
    async def pay(self, interaction: discord.Interaction, member: discord.Member, amount: int):
        if amount <= 0 or member.id == interaction.user.id:
            await interaction.response.send_message("❌ مبلغ غير صالح!")
            return
        
        sender_balance = await self.get_balance(interaction.user.id, interaction.guild_id)
        if sender_balance < amount:
            await interaction.response.send_message(f"❌ رصيدك غير كافٍ! لديك {sender_balance} عملة.")
            return
        
        await self.add_balance(interaction.user.id, interaction.guild_id, -amount)
        await self.add_balance(member.id, interaction.guild_id, amount)
        
        embed = discord.Embed(title="💸 تم التحويل!", description=f"{interaction.user.mention} حول **{amount}** عملة إلى {member.mention}", color=discord.Color.blue())
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="work", description="اعمل لكسب المال")
    async def work(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        guild_id = interaction.guild_id
        now = datetime.now()
        
        # تبريد ساعة
        key = f"{guild_id}_{user_id}"
        if key in self.work_cooldowns:
            diff = now - self.work_cooldowns[key]
            if diff.total_seconds() < 3600:
                remaining = 3600 - int(diff.total_seconds())
                await interaction.response.send_message(f"⏰ انتظر {remaining // 60} دقيقة {remaining % 60} ثانية!")
                return
        
        async with aiosqlite.connect("data/rtg_bot.db") as db:
            async with db.execute("SELECT job, job_level FROM economy WHERE user_id = ? AND guild_id = ?", (user_id, guild_id)) as cursor:
                result = await cursor.fetchone()
        
        job_name = result[0] if result and result[0] else "🍔 Burger Flipper"
        job_level = result[1] if result and result[1] else 1
        job = self.JOBS.get(job_name, self.JOBS["🍔 Burger Flipper"])
        
        min_salary, max_salary = job["salary"]
        salary = random.randint(min_salary, max_salary) + (job_level * job["multiplier"])
        
        await self.add_balance(user_id, guild_id, salary)
        self.work_cooldowns[key] = now
        
        embed = discord.Embed(title="💼 العمل", description=f"{interaction.user.mention} عمل كـ **{job_name}**", color=discord.Color.green())
        embed.add_field(name="💰 الربح", value=f"{salary} عملة", inline=True)
        embed.add_field(name="📈 مستوى الوظيفة", value=str(job_level), inline=True)
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="jobs", description="قائمة الوظائف")
    async def list_jobs(self, interaction: discord.Interaction):
        embed = discord.Embed(title="💼 قائمة الوظائف", description="استخدم `/apply_job <اسم الوظيفة>`", color=discord.Color.blue())
        for job_name, job_data in self.JOBS.items():
            embed.add_field(name=job_name, value=f"💰 {job_data['salary'][0]}-{job_data['salary'][1]} + {job_data['multiplier']}× المستوى", inline=False)
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="apply_job", description="التقدم لوظيفة")
    async def apply_job(self, interaction: discord.Interaction, job_name: str):
        if job_name not in self.JOBS:
            await interaction.response.send_message("❌ وظيفة غير موجودة!")
            return
        
        async with aiosqlite.connect("data/rtg_bot.db") as db:
            await db.execute("UPDATE economy SET job = ?, job_level = 1 WHERE user_id = ? AND guild_id = ?", (job_name, interaction.user.id, interaction.guild_id))
            await db.commit()
        
        embed = discord.Embed(title="✅ تم التقديم!", description=f"تم تعيينك كـ **{job_name}**", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="steal", description="حاول سرقة عملات (مخاطرة!)")
    async def steal(self, interaction: discord.Interaction, target: discord.Member):
        if target.id == interaction.user.id:
            await interaction.response.send_message("❌ لا يمكنك سرقة نفسك!")
            return
        
        target_balance = await self.get_balance(target.id, interaction.guild_id)
        if target_balance < 50:
            await interaction.response.send_message(f"❌ {target.mention} ليس لديه ما يكفي!")
            return
        
        success = random.random() < 0.4
        
        if success:
            stolen = random.randint(20, min(200, target_balance // 2))
            await self.add_balance(interaction.user.id, interaction.guild_id, stolen)
            await self.add_balance(target.id, interaction.guild_id, -stolen)
            embed = discord.Embed(title="🦹‍♂️ سرقة ناجحة!", description=f"سرقت **{stolen}** عملة من {target.mention}!", color=discord.Color.dark_red())
        else:
            penalty = random.randint(30, 100)
            await self.add_balance(interaction.user.id, interaction.guild_id, -penalty)
            embed = discord.Embed(title="😵 فشلت السرقة!", description=f"تم ضبطك! غرامة **{penalty}** عملة", color=discord.Color.red())
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="slots", description="لعبة الحظ")
    async def slots(self, interaction: discord.Interaction, bet: int):
        if bet < 10:
            await interaction.response.send_message("❌ الحد الأدنى 10 عملات!")
            return
        
        balance = await self.get_balance(interaction.user.id, interaction.guild_id)
        if balance < bet:
            await interaction.response.send_message(f"❌ رصيدك غير كافٍ!")
            return
        
        emojis = ["🍒", "🍊", "🍋", "🍉", "⭐", "💎", "7️⃣"]
        results = [random.choice(emojis) for _ in range(3)]
        
        if results[0] == results[1] == results[2]:
            multiplier = 10 if results[0] == "7️⃣" else 5 if results[0] == "💎" else 3
            winnings = bet * multiplier
            await self.add_balance(interaction.user.id, interaction.guild_id, winnings)
            embed = discord.Embed(title="🎰 JACKPOT! 🎰", description=f"{' '.join(results)}\n\n**فزت {winnings} عملة!** (×{multiplier})", color=discord.Color.gold())
        elif results[0] == results[1] or results[1] == results[2] or results[0] == results[2]:
            winnings = bet * 2
            await self.add_balance(interaction.user.id, interaction.guild_id, winnings)
            embed = discord.Embed(title="🎰 فوز!", description=f"{' '.join(results)}\n\n**فزت {winnings} عملة!**", color=discord.Color.blue())
        else:
            await self.add_balance(interaction.user.id, interaction.guild_id, -bet)
            embed = discord.Embed(title="🎰 خسارة!", description=f"{' '.join(results)}\n\n**خسرت {bet} عملة!**", color=discord.Color.red())
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="shop", description="عرض المتجر")
    async def shop(self, interaction: discord.Interaction):
        async with aiosqlite.connect("data/rtg_bot.db") as db:
            async with db.execute("SELECT item_id, item_name, price, description FROM shop WHERE guild_id = ?", (interaction.guild_id,)) as cursor:
                items = await cursor.fetchall()
        
        embed = discord.Embed(title="🛒 المتجر", description="استخدم `/buy <id>` للشراء", color=discord.Color.purple())
        
        if items:
            for item_id, name, price, desc in items[:10]:
                embed.add_field(name=f"#{item_id} - {name}", value=f"💰 {price} عملة\n📝 {desc or 'لا يوجد وصف'}", inline=False)
        else:
            embed.add_field(name="📦 المتجر فارغ", value="استخدم `/add_shop_item` للإضافة", inline=False)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="buy", description="شراء منتج")
    async def buy(self, interaction: discord.Interaction, item_id: int):
        async with aiosqlite.connect("data/rtg_bot.db") as db:
            async with db.execute("SELECT item_name, price, role_id FROM shop WHERE guild_id = ? AND item_id = ?", (interaction.guild_id, item_id)) as cursor:
                item = await cursor.fetchone()
        
        if not item:
            await interaction.response.send_message("❌ المنتج غير موجود!")
            return
        
        name, price, role_id = item
        balance = await self.get_balance(interaction.user.id, interaction.guild_id)
        
        if balance < price:
            await interaction.response.send_message(f"❌ تحتاج {price} عملة!")
            return
        
        await self.add_balance(interaction.user.id, interaction.guild_id, -price)
        
        if role_id:
            role = interaction.guild.get_role(role_id)
            if role:
                await interaction.user.add_roles(role)
        
        embed = discord.Embed(title="✅ تم الشراء!", description=f"اشتريت **{name}** مقابل {price} عملة", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="add_shop_item", description="[ADMIN] إضافة منتج للمتجر")
    @app_commands.default_permissions(administrator=True)
    async def add_shop_item(self, interaction: discord.Interaction, name: str, price: int, role: discord.Role = None, description: str = ""):
        async with aiosqlite.connect("data/rtg_bot.db") as db:
            await db.execute('''
                INSERT INTO shop (guild_id, item_name, item_type, role_id, price, description)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (interaction.guild_id, name, "role" if role else "item", role.id if role else None, price, description))
            await db.commit()
        
        embed = discord.Embed(title="✅ تمت الإضافة", description=f"تمت إضافة **{name}** بسعر {price} عملة", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="leaderboard", description="قائمة الأغنياء")
    async def economy_leaderboard(self, interaction: discord.Interaction):
        async with aiosqlite.connect("data/rtg_bot.db") as db:
            async with db.execute("SELECT user_id, balance FROM economy WHERE guild_id = ? ORDER BY balance DESC LIMIT 10", (interaction.guild_id,)) as cursor:
                results = await cursor.fetchall()
        
        embed = discord.Embed(title="💰 قائمة الأغنياء", color=discord.Color.gold())
        
        if results:
            text = ""
            for i, (user_id, balance) in enumerate(results, 1):
                member = interaction.guild.get_member(user_id)
                name = member.display_name if member else f"مستخدم #{user_id}"
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                text += f"{medal} **{name}** - {balance} عملة\n"
            embed.description = text
        else:
            embed.description = "لا توجد بيانات كافية!"
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(EconomySystem(bot))