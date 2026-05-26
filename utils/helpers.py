import discord
import random
from datetime import datetime

def format_duration(seconds: int) -> str:
    minutes = seconds // 60
    remaining_seconds = seconds % 60
    return f"{minutes}:{remaining_seconds:02d}"

def create_progress_bar(current: int, total: int, length: int = 15) -> str:
    if total <= 0: return "░" * length
    filled = int(current / total * length)
    return "█" * filled + "░" * (length - filled)

def get_random_color() -> discord.Color:
    return discord.Color.from_rgb(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))

async def send_embed(channel: discord.TextChannel, title: str, description: str, color: discord.Color = discord.Color.blue()):
    embed = discord.Embed(title=title, description=description, color=color, timestamp=datetime.now())
    await channel.send(embed=embed)