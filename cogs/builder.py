import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite

class ServerBuilder(commands.Cog):
    """نظام بناء السيرفر التلقائي"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="build_server", description="[OWNER] بناء السيرفر تلقائياً")
    @app_commands.default_permissions(administrator=True)
    async def build_server(self, interaction: discord.Interaction):
        """يبني السيرفر بالكامل بقنواته ورتبه"""
        
        await interaction.response.defer()
        guild = interaction.guild
        
        embed = discord.Embed(
            title="🏗️ جاري بناء السيرفر...",
            description="سيتم إنشاء الرتب والقنوات والفئات",
            color=discord.Color.blue()
        )
        await interaction.followup.send(embed=embed)
        
        try:
            # ========== 1. إنشاء الرتب ==========
            roles = {}
            roles_config = {
                "👑 Owner": 0x000000,
                "💎 VIP": 0xFFD700,
                "🌟 Booster": 0xFF69B4,
                "🛡️ Admin": 0xFF0000,
                "🔧 Mod": 0x00AAFF,
                "👥 Member": 0x00FF00,
                "🤖 Bot": 0x808080,
                "🎭 Muted": 0x666666,
            }
            
            for role_name, color in roles_config.items():
                existing = discord.utils.get(guild.roles, name=role_name)
                if existing:
                    roles[role_name] = existing
                else:
                    role = await guild.create_role(name=role_name, color=discord.Color(color))
                    roles[role_name] = role
            
            # ========== 2. إنشاء الفئات ==========
            categories = {}
            categories_config = ["📁 GENERAL", "🎮 COMMUNITY", "⚙️ ADMIN", "🎫 SUPPORT"]
            
            for cat_name in categories_config:
                existing = discord.utils.get(guild.categories, name=cat_name)
                if existing:
                    categories[cat_name] = existing
                else:
                    cat = await guild.create_category(cat_name)
                    categories[cat_name] = cat
            
            # ========== 3. إنشاء القنوات ==========
            channels_config = [
                # قنوات عامة
                {"name": "welcome", "category": "📁 GENERAL", "type": "text", "slowmode": 0},
                {"name": "rules", "category": "📁 GENERAL", "type": "text", "slowmode": 0},
                {"name": "announcements", "category": "📁 GENERAL", "type": "text", "slowmode": 0},
                
                # قنوات المجتمع
                {"name": "general-chat", "category": "🎮 COMMUNITY", "type": "text", "slowmode": 2},
                {"name": "media", "category": "🎮 COMMUNITY", "type": "text", "slowmode": 5},
                {"name": "voice-chat", "category": "🎮 COMMUNITY", "type": "voice", "slowmode": 0},
                {"name": "music", "category": "🎮 COMMUNITY", "type": "voice", "slowmode": 0},
                
                # قنوات البوت
                {"name": "bot-commands", "category": "🎮 COMMUNITY", "type": "text", "slowmode": 0},
                {"name": "economy", "category": "🎮 COMMUNITY", "type": "text", "slowmode": 0},
                
                # قنوات الإدارة
                {"name": "admin-logs", "category": "⚙️ ADMIN", "type": "text", "slowmode": 0},
                {"name": "mod-commands", "category": "⚙️ ADMIN", "type": "text", "slowmode": 0},
            ]
            
            for ch in channels_config:
                category = categories.get(ch["category"])
                existing = discord.utils.get(guild.channels, name=ch["name"])
                if not existing:
                    if ch["type"] == "text":
                        channel = await guild.create_text_channel(
                            ch["name"], 
                            category=category,
                            slowmode_delay=ch["slowmode"]
                        )
                    else:
                        channel = await guild.create_voice_channel(ch["name"], category=category)
            
            # ========== 4. إنشاء لوحة التحقق ==========
            welcome_channel = discord.utils.get(guild.text_channels, name="welcome")
            if welcome_channel:
                verify_embed = discord.Embed(
                    title="🔐 التحقق من الدخول",
                    description="اضغط على الزر أدناه للتحقق من حسابك والوصول إلى السيرفر",
                    color=discord.Color.green()
                )
                
                class VerifyButton(discord.ui.View):
                    @discord.ui.button(label="✅ تحقق", style=discord.ButtonStyle.success)
                    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
                        member_role = discord.utils.get(guild.roles, name="👥 Member")
                        if member_role:
                            await interaction.user.add_roles(member_role)
                            await interaction.response.send_message("✅ تم التحقق بنجاح! مرحباً بك في السيرفر", ephemeral=True)
                        else:
                            await interaction.response.send_message("❌ حدث خطأ، الرجاء التواصل مع الإدارة", ephemeral=True)
                
                await welcome_channel.send(embed=verify_embed, view=VerifyButton())
            
            # ========== 5. إنشاء لوحة الرتب التفاعلية ==========
            roles_channel = discord.utils.get(guild.text_channels, name="general-chat")
            if roles_channel:
                roles_embed = discord.Embed(
                    title="🎭 الرتب التفاعلية",
                    description="اضغط على الإموجي المناسب للحصول على الرتبة",
                    color=discord.Color.purple()
                )
                roles_embed.add_field(name="🎮 Gamer", value="اضغط على 🎮", inline=True)
                roles_embed.add_field(name="🎵 Music Lover", value="اضغط على 🎵", inline=True)
                roles_embed.add_field(name="🍥 Anime Fan", value="اضغط على 🍥", inline=True)
                
                msg = await roles_channel.send(embed=roles_embed)
                await msg.add_reaction("🎮")
                await msg.add_reaction("🎵")
                await msg.add_reaction("🍥")
            
            # ========== 6. إنشاء لوحة التذاكر ==========
            support_category = categories.get("🎫 SUPPORT")
            if support_category:
                ticket_embed = discord.Embed(
                    title="🎫 التذاكر",
                    description="اضغط على الزر أدناه لفتح تذكرة دعم",
                    color=discord.Color.blue()
                )
                
                class TicketButton(discord.ui.View):
                    @discord.ui.button(label="📩 فتح تذكرة", style=discord.ButtonStyle.primary)
                    async def ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
                        ticket_channel = await guild.create_text_channel(
                            f"ticket-{interaction.user.name}",
                            category=support_category
                        )
                        await ticket_channel.set_permissions(interaction.user, read_messages=True, send_messages=True)
                        await ticket_channel.send(f"مرحباً {interaction.user.mention}! كيف يمكننا مساعدتك؟")
                        await interaction.response.send_message(f"✅ تم فتح تذكرة: {ticket_channel.mention}", ephemeral=True)
                
                ticket_ch = discord.utils.get(guild.text_channels, name="bot-commands")
                if ticket_ch:
                    await ticket_ch.send(embed=ticket_embed, view=TicketButton())
            
            # ========== النتيجة ==========
            result_embed = discord.Embed(
                title="✅ تم بناء السيرفر بنجاح!",
                description=f"""
                **📊 الإحصائيات:**
                • 🎭 الرتب: {len(roles)}
                • 📁 الفئات: {len(categories)}
                • 💬 القنوات: {len(channels_config)}
                
                **🎮 الأوامر المتاحة:**
                • `/help` - عرض المساعدة
                • `/rank` - عرض رتبتك
                • `/balance` - عرض رصيدك
                """,
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=result_embed)
            
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ فشل بناء السيرفر",
                description=f"حدث خطأ: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=error_embed)

async def setup(bot):
    await bot.add_cog(ServerBuilder(bot))
