import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
import uuid
from datetime import datetime

class TicketSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    async def cog_load(self):
        async with aiosqlite.connect("data/rtg_bot.db") as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS tickets (
                    ticket_id TEXT PRIMARY KEY,
                    guild_id INTEGER,
                    user_id INTEGER,
                    channel_id INTEGER,
                    status TEXT,
                    created_at TEXT,
                    transcript TEXT
                )
            ''')
            await db.commit()
    
    class TicketButton(discord.ui.View):
        def __init__(self, cog):
            super().__init__(timeout=None)
            self.cog = cog
        
        @discord.ui.button(label="🎫 فتح تذكرة", style=discord.ButtonStyle.primary, custom_id="ticket_button")
        async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
            # التحقق من وجود تذكرة مفتوحة
            async with aiosqlite.connect("data/rtg_bot.db") as db:
                async with db.execute(
                    "SELECT channel_id FROM tickets WHERE guild_id = ? AND user_id = ? AND status = 'open'",
                    (interaction.guild_id, interaction.user.id)
                ) as cursor:
                    existing = await cursor.fetchone()
            
            if existing:
                await interaction.response.send_message("❌ لديك تذكرة مفتوحة بالفعل!", ephemeral=True)
                return
            
            # إنشاء القناة
            ticket_id = str(uuid.uuid4())[:8]
            category = discord.utils.get(interaction.guild.categories, name="🎫 TICKETS")
            if not category:
                category = await interaction.guild.create_category("🎫 TICKETS")
            
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
                interaction.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
            }
            
            channel = await interaction.guild.create_text_channel(
                f"ticket-{interaction.user.name}-{ticket_id}",
                category=category,
                overwrites=overwrites
            )
            
            async with aiosqlite.connect("data/rtg_bot.db") as db:
                await db.execute('''
                    INSERT INTO tickets (ticket_id, guild_id, user_id, channel_id, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (ticket_id, interaction.guild_id, interaction.user.id, channel.id, "open", datetime.now().isoformat()))
                await db.commit()
            
            embed = discord.Embed(
                title="🎫 تذكرة دعم",
                description=f"مرحباً {interaction.user.mention}!\nفريق الدعم سيساعدك قريباً.\nاستخدم `/ticket close` للإغلاق.",
                color=discord.Color.blue()
            )
            await channel.send(embed=embed)
            
            await interaction.response.send_message(f"✅ تم إنشاء تذكرتك: {channel.mention}", ephemeral=True)
    
    @app_commands.command(name="ticket_panel", description="[ADMIN] إنشاء لوحة التذاكر")
    @app_commands.default_permissions(administrator=True)
    async def ticket_panel(self, interaction: discord.Interaction):
        embed = discord.Embed(title="🎫 مركز الدعم", description="اضغط على الزر لفتح تذكرة", color=discord.Color.blue())
        view = self.TicketButton(self)
        await interaction.response.send_message(embed=embed, view=view)
    
    @app_commands.command(name="ticket_close", description="إغلاق التذكرة")
    async def ticket_close(self, interaction: discord.Interaction):
        if not interaction.channel.name.startswith("ticket-"):
            await interaction.response.send_message("❌ هذه ليست قناة تذكرة!", ephemeral=True)
            return
        
        # حفظ المحادثة
        transcript = []
        async for message in interaction.channel.history(limit=200, oldest_first=True):
            transcript.append(f"[{message.createdat}] {message.author.name}: {message.content}")
        
        transcript_text = "\n".join(transcript)
        
        async with aiosqlite.connect("data/rtg_bot.db") as db:
            await db.execute("UPDATE tickets SET status = 'closed', transcript = ? WHERE channel_id = ?", (transcript_text, interaction.channel.id))
            await db.commit()
        
        await interaction.response.send_message("🔒 جاري إغلاق التذكرة...")
        await asyncio.sleep(3)
        await interaction.channel.delete()

async def setup(bot):
    await bot.add_cog(TicketSystem(bot))