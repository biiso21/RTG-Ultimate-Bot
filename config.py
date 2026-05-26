import os
from dotenv import load_dotenv

load_dotenv()

# ========== إعدادات الترخيص والحماية ==========

# قائمة السيرفرات المسموح بها
ALLOWED_GUILDS = os.getenv("ALLOWED_GUILDS", "1361756331404693665").split(",") if os.getenv("ALLOWED_GUILDS") else ["1361756331404693665"]

# وضع الحماية (1 = تفعيل، 0 = تعطيل مؤقت للاختبار)
PROTECTION_MODE = int(os.getenv("PROTECTION_MODE", "1"))

# كلمة المرور الرئيسية لإدارة الترخيص
MASTER_PASSWORD = os.getenv("MASTER_PASSWORD", "RTG_Ultimate_2024_Secure")

# مفتاح التشفير
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "RTG_Community_Secret_Key_2024_Ultimate")

# خادم الترخيص الرئيسي (سيرفرك الأساسي - لا يمكن تغييره)
OWNER_GUILD_ID = int(os.getenv("OWNER_GUILD_ID", "1361756331404693665"))

# معرف المطور الأساسي (حسابك)
OWNER_ID = int(os.getenv("OWNER_ID", "1276968112071249958"))

# عدد السيرفرات القصوى المسموحة
MAX_GUILDS = int(os.getenv("MAX_GUILDS", "5"))