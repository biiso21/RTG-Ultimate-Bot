import discord
from discord.ext import commands
from discord import app_commands
import random

class FunSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="hug", description="احتضن عضوًا")
    async def hug(self, interaction: discord.Interaction, member: discord.Member):
        gifs = ["https://media.giphy.com/media/3o7abB06u9bNzA8LC8/giphy.gif", "https://media.giphy.com/media/PHZ7v9tf2s81i/giphy.gif"]
        embed = discord.Embed(description=f"🤗 {interaction.user.mention} يحتضن {member.mention}!", color=discord.Color.pink())
        embed.set_image(url=random.choice(gifs))
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="kiss", description="قبّل عضوًا")
    async def kiss(self, interaction: discord.Interaction, member: discord.Member):
        gifs = ["https://media.giphy.com/media/G3va31oEEnIkM/giphy.gif", "https://media.giphy.com/media/bm2O3nXTcKJeU/giphy.gif"]
        embed = discord.Embed(description=f"😘 {interaction.user.mention} قبّل {member.mention}!", color=discord.Color.red())
        embed.set_image(url=random.choice(gifs))
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="slap", description="صفّع عضوًا")
    async def slap(self, interaction: discord.Interaction, member: discord.Member):
        gifs = ["https://media.giphy.com/media/3XlT2zB5K9Vr6/giphy.gif", "https://media.giphy.com/media/xT5LMHxhOfscxPfIfm/giphy.gif"]
        embed = discord.Embed(description=f"👋 {interaction.user.mention} صفع {member.mention}!", color=discord.Color.dark_red())
        embed.set_image(url=random.choice(gifs))
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="8ball", description="اسأل الكرة السحرية")
    async def eight_ball(self, interaction: discord.Interaction, question: str):
        answers = ["نعم بالتأكيد!", "لا أبدًا!", "ربما", "من الصعب توقعه...", "الأجواء تشير إلى نعم", "لا تعتمد على ذلك", "اسأل لاحقًا"]
        embed = discord.Embed(title="🎱 الكرة السحرية", description=f"**سؤالك:** {question}\n**الجواب:** {random.choice(answers)}", color=discord.Color.purple())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="meme", description="ميم عشوائي")
    async def meme(self, interaction: discord.Interaction):
        memes = ["https://i.imgflip.com/1bij.jpg", "https://i.imgflip.com/26am.jpg"]
        embed = discord.Embed(title="😂 ميم اليوم", color=discord.Color.gold())
        embed.set_image(url=random.choice(memes))
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="avatar", description="عرض صورة البروفايل")
    async def avatar(self, interaction: discord.Interaction, member: discord.Member = None):
        target = member or interaction.user
        embed = discord.Embed(title=f"🖼️ صورة {target.display_name}", color=discord.Color.blue())
        embed.set_image(url=target.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="serverinfo", description="معلومات السيرفر")
    async def server_info(self, interaction: discord.Interaction):
        guild = interaction.guild
        embed = discord.Embed(title=f"📊 معلومات {guild.name}", color=discord.Color.blue())
        if guild.icon: embed.set_thumbnail(url=guild.icon.url)
        embed.add_field(name="👑 المالك", value=guild.owner.mention, inline=True)
        embed.add_field(name="👥 الأعضاء", value=str(guild.member_count), inline=True)
        embed.add_field(name="📅 تاريخ الإنشاء", value=guild.created_at.strftime("%Y-%m-%d"), inline=True)
        embed.add_field(name="🔊 القنوات الصوتية", value=str(len(guild.voice_channels)), inline=True)
        embed.add_field(name="💬 القنوات النصية", value=str(len(guild.text_channels)), inline=True)
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(FunSystem(bot))