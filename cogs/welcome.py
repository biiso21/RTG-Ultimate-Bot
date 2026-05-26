import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
import random
from settings import WELCOME_CONFIG

class WelcomeSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        async with aiosqlite.connect("data/rtg_bot.db") as db:
            await db.execute('''CREATE TABLE IF NOT EXISTS welcome_settings (guild_id INTEGER PRIMARY KEY, channel_id INTEGER, welcome_enabled INTEGER DEFAULT 1, farewell_enabled INTEGER DEFAULT 1)''')
            await db.commit()

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        async with aiosqlite.connect("data/rtg_bot.db") as db:
            async with db.execute("SELECT channel_id, welcome_enabled FROM welcome_settings WHERE guild_id = ?", (member.guild.id,)) as cursor:
                result = await cursor.fetchone()
        if result and result[1]:
            channel = member.guild.get_channel(result[0])
            if channel:
                embed = discord.Embed(title=f"👋 مرحباً {member.name}!", description=f"اهلاً بك في **{member.guild.name}**! 🎉\nلدينا الآن {member.guild.member_count} عضو", color=discord.Color.green())
                embed.set_thumbnail(url=member.display_avatar.url)
                embed.set_image(url=WELCOME_CONFIG["default_gif"])
                await channel.send(content=member.mention, embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        async with aiosqlite.connect("data/rtg_bot.db") as db:
            async with db.execute("SELECT channel_id, farewell_enabled FROM welcome_settings WHERE guild_id = ?", (member.guild.id,)) as cursor:
                result = await cursor.fetchone()
        if result and result[1]:
            channel = member.guild.get_channel(result[0])
            if channel:
                embed = discord.Embed(title="😢 وداعاً!", description=f"{member.name} غادر السيرفر...\nلدينا الآن {member.guild.member_count} عضو", color=discord.Color.red())
                await channel.send(embed=embed)

    @app_commands.command(name="set_welcome_channel", description="[ADMIN] تعيين قناة الترحيب")
    @app_commands.default_permissions(administrator=True)
    async def set_welcome_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        async with aiosqlite.connect("data/rtg_bot.db") as db:
            await db.execute('''INSERT INTO welcome_settings (guild_id, channel_id) VALUES (?, ?) ON CONFLICT(guild_id) DO UPDATE SET channel_id = excluded.channel_id''', (interaction.guild_id, channel.id))
            await db.commit()
        await interaction.response.send_message(f"✅ تم تعيين {channel.mention} كقناة ترحيب")

    @app_commands.command(name="toggle_welcome", description="[ADMIN] تفعيل/تعطيل الترحيب")
    @app_commands.default_permissions(administrator=True)
    async def toggle_welcome(self, interaction: discord.Interaction, state: str):
        enabled = state.lower() == "on"
        async with aiosqlite.connect("data/rtg_bot.db") as db:
            await db.execute('''INSERT INTO welcome_settings (guild_id, welcome_enabled) VALUES (?, ?) ON CONFLICT(guild_id) DO UPDATE SET welcome_enabled = excluded.welcome_enabled''', (interaction.guild_id, int(enabled)))
            await db.commit()
        await interaction.response.send_message(f"✅ تم {'تفعيل' if enabled else 'تعطيل'} رسائل الترحيب")

async def setup(bot):
    await bot.add_cog(WelcomeSystem(bot))