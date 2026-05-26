import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
from datetime import datetime, timedelta

class ModerationSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        async with aiosqlite.connect("data/rtg_bot.db") as db:
            await db.execute('''CREATE TABLE IF NOT EXISTS warnings (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, guild_id INTEGER, moderator_id INTEGER, reason TEXT, timestamp TEXT)''')
            await db.commit()

    @app_commands.command(name="clear", description="مسح الرسائل")
    @app_commands.default_permissions(manage_messages=True)
    async def clear(self, interaction: discord.Interaction, amount: int):
        if amount <= 0 or amount > 100: await interaction.response.send_message("❌ العدد بين 1 و 100"); return
        await interaction.channel.purge(limit=amount + 1)
        await interaction.response.send_message(f"✅ تم مسح {amount} رسالة", ephemeral=True)

    @app_commands.command(name="ban", description="حظر عضو")
    @app_commands.default_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = None):
        if member == interaction.user: await interaction.response.send_message("❌ لا يمكنك حظر نفسك!"); return
        await member.ban(reason=reason)
        await interaction.response.send_message(f"🔨 تم حظر {member.mention}")

    @app_commands.command(name="kick", description="طرد عضو")
    @app_commands.default_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = None):
        if member == interaction.user: await interaction.response.send_message("❌ لا يمكنك طرد نفسك!"); return
        await member.kick(reason=reason)
        await interaction.response.send_message(f"👢 تم طرد {member.mention}")

    @app_commands.command(name="mute", description="كتم عضو")
    @app_commands.default_permissions(moderate_members=True)
    async def mute(self, interaction: discord.Interaction, member: discord.Member, duration: str, reason: str = None):
        units = {"m": 60, "h": 3600, "d": 86400}
        unit = duration[-1]
        if unit not in units: await interaction.response.send_message("❌ استخدم: 30m, 1h, 1d"); return
        try: value = int(duration[:-1])
        except: await interaction.response.send_message("❌ صيغة غير صحيحة!"); return
        seconds = value * units[unit]
        await member.timeout(discord.utils.utcnow() + timedelta(seconds=seconds), reason=reason)
        await interaction.response.send_message(f"🔇 تم كتم {member.mention} لمدة {duration}")

    @app_commands.command(name="unmute", description="إلغاء الكتم")
    @app_commands.default_permissions(moderate_members=True)
    async def unmute(self, interaction: discord.Interaction, member: discord.Member):
        await member.timeout(None)
        await interaction.response.send_message(f"🔊 تم إلغاء كتم {member.mention}")

    @app_commands.command(name="warn", description="تحذير عضو")
    @app_commands.default_permissions(moderate_members=True)
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        async with aiosqlite.connect("data/rtg_bot.db") as db:
            await db.execute("INSERT INTO warnings (user_id, guild_id, moderator_id, reason, timestamp) VALUES (?, ?, ?, ?, ?)", (member.id, interaction.guild_id, interaction.user.id, reason, datetime.now().isoformat()))
            await db.commit()
        await interaction.response.send_message(f"⚠️ تم تحذير {member.mention}\nالسبب: {reason}")

    @app_commands.command(name="warnings", description="عرض تحذيرات عضو")
    @app_commands.default_permissions(moderate_members=True)
    async def warnings(self, interaction: discord.Interaction, member: discord.Member):
        async with aiosqlite.connect("data/rtg_bot.db") as db:
            async with db.execute("SELECT reason, timestamp, moderator_id FROM warnings WHERE user_id = ? AND guild_id = ? LIMIT 10", (member.id, interaction.guild_id)) as cursor:
                warns = await cursor.fetchall()
        if warns:
            embed = discord.Embed(title=f"⚠️ تحذيرات {member.display_name}", color=discord.Color.orange())
            for reason, timestamp, mod_id in warns: embed.add_field(name=f"📅 {timestamp[:10]}", value=f"السبب: {reason}\nبواسطة: <@{mod_id}>", inline=False)
            await interaction.response.send_message(embed=embed)
        else: await interaction.response.send_message(f"✅ {member.mention} ليس لديه تحذيرات")

    @app_commands.command(name="lockdown", description="قفل القناة")
    @app_commands.default_permissions(administrator=True)
    async def lockdown(self, interaction: discord.Interaction):
        await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=False)
        await interaction.response.send_message("🔒 تم قفل القناة")

    @app_commands.command(name="unlock", description="فتح القناة")
    @app_commands.default_permissions(administrator=True)
    async def unlock(self, interaction: discord.Interaction):
        await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=None)
        await interaction.response.send_message("🔓 تم فتح القناة")

async def setup(bot):
    await bot.add_cog(ModerationSystem(bot))