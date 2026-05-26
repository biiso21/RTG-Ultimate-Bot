import json
import hashlib
import base64
import os
import secrets
from cryptography.fernet import Fernet
from datetime import datetime, timedelta
from config import ENCRYPTION_KEY, MASTER_PASSWORD, MAX_GUILDS

class LicenseManager:
    """مدير الترخيص والتفعيل"""
    
    def __init__(self):
        self.license_file = "license_keys.json"
        self.encryption_key = self._generate_key(ENCRYPTION_KEY)
        self.cipher = Fernet(self.encryption_key)
        self.licenses = self._load_licenses()
    
    def _generate_key(self, password: str) -> bytes:
        """توليد مفتاح تشفير من كلمة مرور"""
        key = hashlib.sha256(password.encode()).digest()
        return base64.urlsafe_b64encode(key)
    
    def _load_licenses(self):
        """تحميل مفاتيح الترخيص من الملف"""
        if os.path.exists(self.license_file):
            try:
                with open(self.license_file, 'rb') as f:
                    encrypted_data = f.read()
                    decrypted = self.cipher.decrypt(encrypted_data)
                    return json.loads(decrypted)
            except:
                return {"licenses": {}, "master_key": MASTER_PASSWORD}
        return {"licenses": {}, "master_key": MASTER_PASSWORD}
    
    def _save_licenses(self):
        """حفظ مفاتيح الترخيص مشفرة"""
        data = json.dumps(self.licenses)
        encrypted = self.cipher.encrypt(data.encode())
        with open(self.license_file, 'wb') as f:
            f.write(encrypted)
    
    def generate_license_key(self, guild_id: int, guild_name: str, expires_days: int = 365) -> str:
        """توليد مفتاح ترخيص جديد لسيرفر"""
        key = secrets.token_hex(16).upper()
        
        self.licenses["licenses"][key] = {
            "guild_id": guild_id,
            "guild_name": guild_name,
            "activated": False,
            "expires": (datetime.now() + timedelta(days=expires_days)).isoformat(),
            "created_at": datetime.now().isoformat(),
            "last_seen": None
        }
        
        self._save_licenses()
        return key
    
    def activate_license(self, key: str, guild_id: int) -> bool:
        """تفعيل مفتاح الترخيص لسيرفر"""
        if key not in self.licenses["licenses"]:
            return False
        
        license_data = self.licenses["licenses"][key]
        
        # التحقق من الصلاحية
        expires = datetime.fromisoformat(license_data["expires"])
        if expires < datetime.now():
            return False
        
        # التحقق من أن المفتاح للسيرفر الصحيح
        if license_data["guild_id"] != guild_id:
            return False
        
        license_data["activated"] = True
        license_data["last_seen"] = datetime.now().isoformat()
        self._save_licenses()
        return True
    
    def check_license(self, guild_id: int) -> bool:
        """التحقق من وجود ترخيص مفعل للسيرفر"""
        for key, data in self.licenses["licenses"].items():
            if data["guild_id"] == guild_id and data["activated"]:
                # التحقق من صلاحية الترخيص
                expires = datetime.fromisoformat(data["expires"])
                if expires < datetime.now():
                    data["activated"] = False
                    self._save_licenses()
                    return False
                
                # تحديث آخر ظهور
                data["last_seen"] = datetime.now().isoformat()
                self._save_licenses()
                return True
        return False
    
    def revoke_license(self, guild_id: int) -> bool:
        """إلغاء ترخيص سيرفر"""
        for key, data in self.licenses["licenses"].items():
            if data["guild_id"] == guild_id:
                data["activated"] = False
                self._save_licenses()
                return True
        return False
    
    def get_license_info(self, guild_id: int) -> dict:
        """الحصول على معلومات الترخيص لسيرفر"""
        for key, data in self.licenses["licenses"].items():
            if data["guild_id"] == guild_id:
                return {
                    "key": key,
                    "activated": data["activated"],
                    "expires": data["expires"],
                    "created_at": data["created_at"],
                    "last_seen": data["last_seen"]
                }
        return None
    
    def list_licenses(self) -> list:
        """قائمة جميع التراخيص"""
        return [
            {
                "key": key,
                "guild_id": data["guild_id"],
                "guild_name": data["guild_name"],
                "activated": data["activated"],
                "expires": data["expires"]
            }
            for key, data in self.licenses["licenses"].items()
        ]
    
    def get_active_guilds_count(self) -> int:
        """عدد السيرفرات النشطة"""
        count = 0
        for data in self.licenses["licenses"].values():
            if data["activated"]:
                count += 1
        return count

# إنشاء مدير الترخيص العالمي
license_manager = LicenseManager()