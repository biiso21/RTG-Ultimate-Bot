import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
from datetime import datetime

class ServerDashboard(commands.Cog):
    """لوحة تحكم متكاملة لإدارة السيرفر"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="server_info", description="عرض معلومات السيرفر")
    async def server_info(self, interaction: discord.Interaction):
        guild = interaction.guild
        
        embed = discord.Embed(
            title=f"📊 معلومات {guild.name}",
            color=discord.Color.blue()
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        embed.add_field(name="👑 المالك", value=guild.owner.mention, inline=True)
        embed.add_field(name="👥 الأعضاء", value=guild.member_count, inline=True)
        embed.add_field(name="💬 القنوات", value=len(guild.channels), inline=True)
        embed.add_field(name="🎭 الرتب", value=len(guild.roles), inline=True)
        embed.add_field(name="📅 تاريخ الإنشاء", value=guild.created_at.strftime("%Y-%m-%d"), inline=True)
        embed.add_field(name="🔊 البوستات", value=guild.premium_subscription_count, inline=True)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="dashboard", description="عرض لوحة التحكم الرئيسية")
    async def dashboard(self, interaction: discord.Interaction):
        """لوحة تحكم تفاعلية"""
        
        embed = discord.Embed(
            title="🎮 لوحة تحكم RTG Bot",
            description="اختر القسم الذي تريد إدارته",
            color=discord.Color.purple()
        )
        embed.add_field(name="💰 الاقتصاد", value="إدارة الرصيد والمتجر", inline=True)
        embed.add_field(name="📈 المستويات", value="إعدادات الخبرة والرتب", inline=True)
        embed.add_field(name="🛡️ الحماية", value="إعدادات Anti-Nuke", inline=True)
        embed.add_field(name="🎫 التذاكر", value="إدارة نظام الدعم", inline=True)
        embed.add_field(name="👋 الترحيب", value="إعدادات رسائل الترحيب", inline=True)
        embed.add_field(name="🎁 السحوبات", value="إنشاء وإدارة السحوبات", inline=True)
        
        view = DashboardView(self.bot, interaction.guild_id)
        await interaction.response.send_message(embed=embed, view=view)

class DashboardView(discord.ui.View):
    def __init__(self, bot, guild_id):
        super().__init__(timeout=60)
        self.bot = bot
        self.guild_id = guild_id
    
    @discord.ui.button(label="💰 الاقتصاد", style=discord.ButtonStyle.success, row=0)
    async def economy_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="💰 إدارة الاقتصاد", color=discord.Color.gold())
        embed.add_field(name="📊 الرصيد", value="`/balance` - عرض رصيدك", inline=False)
        embed.add_field(name="💼 العمل", value="`/work` - العمل لكسب المال", inline=False)
        embed.add_field(name="🛒 المتجر", value="`/shop` - عرض المتجر", inline=False)
        embed.add_field(name="🎰 القمار", value="`/slots` - لعبة الحظ", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="📈 المستويات", style=discord.ButtonStyle.primary, row=0)
    async def leveling_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="📈 نظام المستويات", color=discord.Color.blue())
        embed.add_field(name="🏆 رتبتي", value="`/rank` - عرض رتبتك", inline=False)
        embed.add_field(name="📊 المتصدرين", value="`/leaderboard` - قائمة المتصدرين", inline=False)
        embed.add_field(name="⚙️ الإعدادات", value="`/set_level_channel` - تعيين قناة الإعلانات", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="🛡️ الحماية", style=discord.ButtonStyle.danger, row=0)
    async def protection_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="🛡️ نظام الحماية", color=discord.Color.red())
        embed.add_field(name="🔄 تفعيل/تعطيل", value="`/antinuke on/off`", inline=False)
        embed.add_field(name="📋 السجلات", value="`/set_log_channel` - تعيين قناة السجلات", inline=False)
        embed.add_field(name="💾 النسخ الاحتياطي", value="`/backup` - إنشاء نسخة احتياطية", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="🎫 التذاكر", style=discord.ButtonStyle.secondary, row=1)
    async def tickets_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="🎫 نظام التذاكر", color=discord.Color.purple())
        embed.add_field(name="📌 إنشاء لوحة", value="`/ticket_panel` - إنشاء لوحة التذاكر", inline=False)
        embed.add_field(name="🔒 إغلاق", value="`/ticket_close` - إغلاق التذكرة", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="👋 الترحيب", style=discord.ButtonStyle.success, row=1)
    async def welcome_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="👋 نظام الترحيب", color=discord.Color.green())
        embed.add_field(name="📢 تعيين القناة", value="`/set_welcome_channel`", inline=False)
        embed.add_field(name="🔄 تفعيل/تعطيل", value="`/toggle_welcome on/off`", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="🎁 السحوبات", style=discord.ButtonStyle.primary, row=1)
    async def giveaways_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="🎁 نظام السحوبات", color=discord.Color.gold())
        embed.add_field(name="✨ إنشاء", value="`/giveaway_create`", inline=False)
        embed.add_field(name="🔄 إعادة سحب", value="`/giveaway_reroll`", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="🗑️ حذف السيرفر", style=discord.ButtonStyle.danger, row=2)
    async def delete_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.guild_permissions.administrator:
            embed = discord.Embed(
                title="⚠️ تحذير!",
                description="هل أنت متأكد من حذف جميع قنوات ورتب هذا السيرفر؟\nهذا الإجراء لا يمكن التراجع عنه!",
                color=discord.Color.red()
            )
            
            class ConfirmDelete(discord.ui.View):
                @discord.ui.button(label="✅ نعم, احذف", style=discord.ButtonStyle.danger)
                async def confirm(self, ctx: discord.Interaction, btn: discord.ui.Button):
                    await ctx.response.send_message("🗑️ جاري حذف القنوات والرتب...", ephemeral=True)
                    for channel in ctx.guild.channels:
                        try:
                            await channel.delete()
                        except:
                            pass
                    for role in ctx.guild.roles:
                        if role.name != "@everyone":
                            try:
                                await role.delete()
                            except:
                                pass
                    await ctx.followup.send("✅ تم حذف جميع القنوات والرتب!", ephemeral=True)
                
                @discord.ui.button(label="❌ إلغاء", style=discord.ButtonStyle.secondary)
                async def cancel(self, ctx: discord.Interaction, btn: discord.ui.Button):
                    await ctx.response.send_message("❌ تم الإلغاء", ephemeral=True)
            
            await interaction.response.send_message(embed=embed, view=ConfirmDelete(), ephemeral=True)
        else:
            await interaction.response.send_message("❌ ليس لديك صلاحية لحذف السيرفر!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(ServerDashboard(bot))
