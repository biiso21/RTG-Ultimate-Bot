import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DEV_IDS = [int(id.strip()) for id in os.getenv("DEV_IDS", "123456789012345678").split(",")]

LEVELING_CONFIG = {
    "rate": 1,
    "per": 60.0,
    "base_xp": 15,
    "random_xp": 10,
    "voice_xp_enabled": True,
    "voice_xp_interval": 60,
    "voice_xp_amount": 10,
    "announce_level_up": True,
}

LEVEL_AWARDS = [
    {"level": 5, "role_name": "🌟 Rising Star"},
    {"level": 10, "role_name": "💬 Active Member"},
    {"level": 25, "role_name": "🔥 Veteran"},
    {"level": 50, "role_name": "👑 Elite"},
    {"level": 100, "role_name": "⚡ Legend"},
]

ANTINUKE_CONFIG = {
    "max_channels_create": 5,
    "max_roles_create": 5,
    "max_webhooks_create": 3,
    "time_window": 5,
    "auto_ban_on_raid": True,
}

MUSIC_CONFIG = {
    "default_volume": 50,
    "max_queue_size": 100,
    "auto_disconnect_minutes": 5,
}

WELCOME_CONFIG = {
    "default_gif": "https://media.giphy.com/media/26BRuo6sLetdllPAQ/giphy.gif",
    "farewell_gif": "https://media.giphy.com/media/3o7abB06u9bNzA8LC8/giphy.gif",
}

DATABASE_PATH = "data/rtg_bot.db"