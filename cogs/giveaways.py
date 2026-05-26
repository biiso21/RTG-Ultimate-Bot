import discord
from discord.ext import commands, tasks
from discord import app_commands
import aiosqlite
import random
from datetime import datetime, timedelta

class GiveawaySystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_giveaways.start()

    async def cog_load(self):
        async with aiosqlite.connect("data/rtg_bot.db") as db:
            await db.execute('''CREATE TABLE IF NOT EXISTS giveaways (message_id INTEGER PRIMARY KEY, guild_id INTEGER, channel_id INTEGER, prize TEXT, winners_count INTEGER, end_time TEXT, entries TEXT, ended INTEGER DEFAULT 0)''')
            await db.commit()

    class GiveawayButton(discord.ui.Button):
        def __init__(self, message_id: int):
            super().__init__(label="🎉 شارك!", style=discord.ButtonStyle.success, custom_id=f"giveaway_{message_id}")
            self.message_id = message_id
        async def callback(self, interaction: discord.Interaction):
            async with aiosqlite.connect("data/rtg_bot.db") as db:
                async with db.execute("SELECT entries FROM giveaways WHERE message_id = ?", (self.message_id,)) as cursor:
                    result = await cursor.fetchone()
                if result:
                    entries = result[0].split(",") if result[0] else []
                    if str(interaction.user.id) not in entries:
                        entries.append(str(interaction.user.id))
                        await db.execute("UPDATE giveaways SET entries = ? WHERE message_id = ?", (",".join(entries), self.message_id))
                        await db.commit()
                        await interaction.response.send_message("✅ تم تسجيل مشاركتك!", ephemeral=True)
                    else: await interaction.response.send_message("❌ أنت مشترك بالفعل!", ephemeral=True)

    @app_commands.command(name="giveaway_create", description="[ADMIN] إنشاء سحوبات")
    @app_commands.default_permissions(administrator=True)
    async def giveaway_create(self, interaction: discord.Interaction, prize: str, duration: str, winners: int = 1):
        units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
        unit = duration[-1]
        if unit not in units: await interaction.response.send_message("❌ استخدم: 30m, 1h, 2d"); return
        try: value = int(duration[:-1])
        except: await interaction.response.send_message("❌ صيغة غير صحيحة!"); return
        seconds = value * units[unit]
        end_time = datetime.now() + timedelta(seconds=seconds)
        embed = discord.Embed(title="🎉 سحوبات! 🎉", description=f"**الجائزة:** {prize}\n**الفائزون:** {winners}\n**ينتهي في:** <t:{int(end_time.timestamp())}:R>", color=discord.Color.purple())
        view = discord.ui.View(timeout=None)
        button = self.GiveawayButton(0)
        view.add_item(button)
        message = await interaction.channel.send(embed=embed, view=view)
        button.message_id = message.id
        async with aiosqlite.connect("data/rtg_bot.db") as db:
            await db.execute("INSERT INTO giveaways (message_id, guild_id, channel_id, prize, winners_count, end_time, entries) VALUES (?, ?, ?, ?, ?, ?, ?)", (message.id, interaction.guild_id, interaction.channel.id, prize, winners, end_time.isoformat(), ""))
            await db.commit()
        await interaction.response.send_message(f"✅ تم إنشاء السحوبات! تنتهي في {duration}", ephemeral=True)

    @tasks.loop(seconds=30)
    async def check_giveaways(self):
        now = datetime.now()
        async with aiosqlite.connect("data/rtg_bot.db") as db:
            async with db.execute("SELECT message_id, channel_id, prize, winners_count, entries FROM giveaways WHERE ended = 0 AND end_time <= ?", (now.isoformat(),)) as cursor:
                ended = await cursor.fetchall()
            for message_id, channel_id, prize, winners_count, entries_str in ended:
                channel = self.bot.get_channel(channel_id)
                if channel:
                    entries = entries_str.split(",") if entries_str else []
                    if entries:
                        winners_list = random.sample(entries, min(winners_count, len(entries)))
                        winner_text = ", ".join([f"<@{w}>" for w in winners_list])
                    else: winner_text = "لا يوجد مشاركون!"
                    embed = discord.Embed(title="🎉 انتهى السحوبات! 🎉", description=f"**الجائزة:** {prize}\n**الفائزون:** {winner_text}", color=discord.Color.gold())
                    await channel.send(embed=embed)
                await db.execute("UPDATE giveaways SET ended = 1 WHERE message_id = ?", (message_id,))
                await db.commit()

    @app_commands.command(name="giveaway_reroll", description="[ADMIN] إعادة سحب")
    @app_commands.default_permissions(administrator=True)
    async def giveaway_reroll(self, interaction: discord.Interaction, message_id: str):
        async with aiosqlite.connect("data/rtg_bot.db") as db:
            async with db.execute("SELECT prize, winners_count, entries FROM giveaways WHERE message_id = ?", (int(message_id),)) as cursor:
                result = await cursor.fetchone()
            if not result: await interaction.response.send_message("❌ لم يتم العثور على السحوبات!"); return
            prize, winners_count, entries_str = result
            entries = entries_str.split(",") if entries_str else []
            if entries:
                winners = random.sample(entries, min(winners_count, len(entries)))
                winner_text = ", ".join([f"<@{w}>" for w in winners])
            else: winner_text = "لا يوجد مشاركون!"
            await interaction.response.send_message(f"🎉 إعادة سحب!\n**الجائزة:** {prize}\n**الفائزون:** {winner_text}")

async def setup(bot):
    await bot.add_cog(GiveawaySystem(bot))