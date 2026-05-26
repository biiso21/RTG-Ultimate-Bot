import discord
from discord.ext import commands
from discord import app_commands
from license import license_manager
from config import OWNER_ID, MASTER_PASSWORD, MAX_GUILDS

class LicenseManagerCog(commands.Cog):
    """أوامر إدارة الترخيص - للمطور فقط"""
    
    def __init__(self, bot):
        self.bot = bot
    
    # ========== التحقق من صلاحيات المطور ==========
    def is_owner(self, user_id: int) -> bool:
        return user_id == OWNER_ID
    
    # ========== أوامر الترخيص ==========
    
    @app_commands.command(name="generate_license", description="[OWNER] توليد مفتاح ترخيص لسيرفر")
    async def generate_license(self, interaction: discord.Interaction, guild_id: str, expires_days: int = 365):
        if not self.is_owner(interaction.user.id):
            await interaction.response.send_message("❌ هذا الأمر للمطور فقط!", ephemeral=True)
            return
        
        try:
            guild_id_int = int(guild_id)
            guild = self.bot.get_guild(guild_id_int)
            guild_name = guild.name if guild else f"Guild_{guild_id_int}"
            
            # التحقق من عدد السيرفرات
            if MAX_GUILDS > 0 and license_manager.get_active_guilds_count() >= MAX_GUILDS:
                await interaction.response.send_message(f"❌ تم الوصول للحد الأقصى ({MAX_GUILDS} سيرفرات)!", ephemeral=True)
                return
            
            key = license_manager.generate_license_key(guild_id_int, guild_name, expires_days)
            
            embed = discord.Embed(
                title="🔑 تم توليد مفتاح ترخيص جديد",
                description=f"**للسيرفر:** {guild_name}\n**المعرف:** {guild_id_int}",
                color=discord.Color.green()
            )
            embed.add_field(name="مفتاح التفعيل", value=f"`{key}`", inline=False)
            embed.add_field(name="مدة الصلاحية", value=f"{expires_days} يوم", inline=True)
            embed.add_field(name="عدد السيرفرات النشطة", value=f"{license_manager.get_active_guilds_count()}/{MAX_GUILDS if MAX_GUILDS > 0 else '∞'}", inline=True)
            embed.set_footer(text="أرسل هذا المفتاح لمالك السيرفر لتفعيل البوت")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except ValueError:
            await interaction.response.send_message("❌ معرف السيرفر غير صالح!", ephemeral=True)
    
    @app_commands.command(name="activate", description="تفعيل البوت على السيرفر الحالي (لأصحاب السيرفرات)")
    async def activate_bot(self, interaction: discord.Interaction, license_key: str):
        """يقوم مالك السيرفر بتفعيل البوت بمفتاح الترخيص"""
        
        guild_id = interaction.guild_id
        
        # التحقق مما إذا كان البوت مفعل بالفعل
        if license_manager.check_license(guild_id):
            await interaction.response.send_message("✅ البوت مفعل بالفعل على هذا السيرفر!", ephemeral=True)
            return
        
        # محاولة التفعيل
        if license_manager.activate_license(license_key, guild_id):
            embed = discord.Embed(
                title="✅ تم تفعيل البوت بنجاح!",
                description="شكراً لتفعيل RTG Ultimate Bot على سيرفرك! 🎉\n\nيمكنك الآن استخدام جميع الأوامر.",
                color=discord.Color.green()
            )
            embed.add_field(name="📊 الإحصائيات", value=f"عدد السيرفرات النشطة: {license_manager.get_active_guilds_count()}")
            await interaction.response.send_message(embed=embed)
            
            # تسجيل في سجل المطور
            owner = await self.bot.fetch_user(OWNER_ID)
            if owner:
                await owner.send(f"🔔 **تم تفعيل البوت على سيرفر جديد!**\nالسيرفر: {interaction.guild.name}\nالمعرف: {guild_id}\nبواسطة: {interaction.user.name}")
        else:
            await interaction.response.send_message("❌ مفتاح التفعيل غير صالح أو منتهي الصلاحية!", ephemeral=True)
    
    @app_commands.command(name="revoke", description="[OWNER] إلغاء تفعيل البوت من سيرفر")
    async def revoke_license(self, interaction: discord.Interaction, guild_id: str):
        if not self.is_owner(interaction.user.id):
            await interaction.response.send_message("❌ هذا الأمر للمطور فقط!", ephemeral=True)
            return
        
        try:
            guild_id_int = int(guild_id)
            if license_manager.revoke_license(guild_id_int):
                await interaction.response.send_message(f"✅ تم إلغاء تفعيل البوت من السيرفر {guild_id_int}", ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ لا يوجد ترخيص مفعل للسيرفر {guild_id_int}", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ معرف السيرفر غير صالح!", ephemeral=True)
    
    @app_commands.command(name="licenses_list", description="[OWNER] عرض قائمة التراخيص")
    async def list_licenses(self, interaction: discord.Interaction):
        if not self.is_owner(interaction.user.id):
            await interaction.response.send_message("❌ هذا الأمر للمطور فقط!", ephemeral=True)
            return
        
        licenses = license_manager.list_licenses()
        
        if not licenses:
            await interaction.response.send_message("📭 لا توجد تراخيص حالياً", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🔑 قائمة التراخيص",
            description=f"إجمالي التراخيص: {len(licenses)}\nالسيرفرات النشطة: {license_manager.get_active_guilds_count()}",
            color=discord.Color.blue()
        )
        
        for lic in licenses[:10]:  # عرض أول 10 فقط
            status = "✅ مفعل" if lic["activated"] else "⏳ غير مفعل"
            embed.add_field(
                name=f"{lic['guild_name']}",
                value=f"المعرف: `{lic['guild_id']}`\nالمفتاح: `{lic['key'][:8]}...`\nالحالة: {status}\nينتهي: {lic['expires'][:10]}",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="license_info", description="عرض معلومات ترخيص السيرفر الحالي")
    async def license_info(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id
        info = license_manager.get_license_info(guild_id)
        
        if info:
            status = "✅ مفعل" if info["activated"] else "⏳ غير مفعل"
            embed = discord.Embed(
                title="🔑 معلومات الترخيص",
                description=f"**السيرفر:** {interaction.guild.name}",
                color=discord.Color.green() if info["activated"] else discord.Color.red()
            )
            embed.add_field(name="الحالة", value=status, inline=True)
            embed.add_field(name="تاريخ الإنشاء", value=info["created_at"][:10], inline=True)
            embed.add_field(name="تاريخ الانتهاء", value=info["expires"][:10], inline=True)
            if info["last_seen"]:
                embed.add_field(name="آخر ظهور", value=info["last_seen"][:10], inline=True)
        else:
            embed = discord.Embed(
                title="🔑 معلومات الترخيص",
                description="❌ لا يوجد ترخيص مفعل لهذا السيرفر!\n\nاستخدم `/activate` لتفعيل البوت بمفتاح الترخيص.",
                color=discord.Color.red()
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(LicenseManagerCog(bot))