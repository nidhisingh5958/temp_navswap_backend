"""
QR Code Service
Handles QR token generation, verification, and expiry management
"""
import logging
from PIL import Image
import os
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import qrcode
from io import BytesIO
import base64
from app.database import get_database
from app.config import get_settings
import redis.asyncio as redis

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

LOGO_PATH = os.path.join(
    BASE_DIR,
    "logo",
    "logo.png"
)

class QRService:
    """Manages QR code generation and verification for swaps"""
    
    def __init__(self):
        self.settings = get_settings()
        self.redis_client: Optional[redis.Redis] = None
    
    async def initialize(self):
        """Initialize Redis connection for QR token caching"""
        try:
            self.redis_client = redis.Redis(
                host=self.settings.REDIS_HOST,
                port=self.settings.REDIS_PORT,
                db=self.settings.REDIS_DB,
                password=self.settings.REDIS_PASSWORD,
                decode_responses=True
            )
            await self.redis_client.ping()
            logger.info("✅ QRService: Redis connected")
        except Exception as e:
            logger.error(f"❌ QRService: Redis connection failed: {e}")
    
    def generate_qr_token(
        self,
        user_id: str,
        station_id: str,
        swap_id: str
    ) -> str:
        """
        Generate a unique, time-bound QR token
        Format: {timestamp}:{user_id}:{station_id}:{swap_id}:{random}:{signature}
        """
        timestamp = int(datetime.utcnow().timestamp())
        random_component = secrets.token_urlsafe(16)
        
        # Create payload
        payload = f"{timestamp}:{user_id}:{station_id}:{swap_id}:{random_component}"
        
        # Add signature for security
        signature = self._sign_token(payload)
        
        qr_token = f"{payload}:{signature}"
        
        logger.info(f"🔐 Generated QR token for user {user_id} at station {station_id}")
        
        return qr_token
    
    def _sign_token(self, payload: str) -> str:
        """Sign token with secret key"""
        secret = self.settings.JWT_SECRET_KEY.encode()
        signature = hashlib.sha256(secret + payload.encode()).hexdigest()[:16]
        return signature
    
    def _verify_signature(self, payload: str, signature: str) -> bool:
        """Verify token signature"""
        expected_signature = self._sign_token(payload)
        return secrets.compare_digest(signature, expected_signature)
    
    async def store_qr_token(
        self,
        qr_token: str,
        swap_id: str,
        user_id: str,
        station_id: str
    ) -> bool:
        """Store QR token in Redis with expiry"""
        try:
            token_data = {
                "swap_id": swap_id,
                "user_id": user_id,
                "station_id": station_id,
                "created_at": datetime.utcnow().isoformat()
            }
            
            # Store in Redis with TTL
            if self.redis_client:
                expiry_seconds = self.settings.QR_TOKEN_EXPIRY_MINUTES * 60
                await self.redis_client.setex(
                    f"qr_token:{qr_token}",
                    expiry_seconds,
                    f"{swap_id}|{user_id}|{station_id}"
                )
            
            # Also store in MongoDB for audit
            db = get_database()
            await db.qr_tokens.insert_one({
                "token": qr_token,
                "swap_id": swap_id,
                "user_id": user_id,
                "station_id": station_id,
                "created_at": datetime.utcnow(),
                "expires_at": datetime.utcnow() + timedelta(
                    minutes=self.settings.QR_TOKEN_EXPIRY_MINUTES
                ),
                "used": False
            })
            
            return True
        
        except Exception as e:
            logger.error(f"Error storing QR token: {e}")
            return False
    
    async def verify_qr_token(
        self,
        qr_token: str,
        station_id: str
    ) -> Dict[str, Any]:
        """
        Verify QR token validity
        Returns: {valid: bool, swap_id: str, user_id: str, message: str}
        """
        try:
            # Parse token
            parts = qr_token.split(":")
            if len(parts) != 6:
                return {
                    "valid": False,
                    "message": "Invalid token format"
                }
            
            timestamp_str, token_user_id, token_station_id, swap_id, random_comp, signature = parts
            
            # Verify signature
            payload = ":".join(parts[:-1])
            if not self._verify_signature(payload, signature):
                return {
                    "valid": False,
                    "message": "Invalid token signature"
                }
            
            # Check station match
            if token_station_id != station_id:
                return {
                    "valid": False,
                    "message": "Token not valid for this station"
                }
            
            # Check expiry
            token_timestamp = int(timestamp_str)
            current_timestamp = int(datetime.utcnow().timestamp())
            expiry_seconds = self.settings.QR_TOKEN_EXPIRY_MINUTES * 60
            
            if current_timestamp - token_timestamp > expiry_seconds:
                return {
                    "valid": False,
                    "message": "QR token has expired"
                }
            
            # Check if already used (Redis)
            if self.redis_client:
                token_data = await self.redis_client.get(f"qr_token:{qr_token}")
                if not token_data:
                    # Check MongoDB
                    db = get_database()
                    db_token = await db.qr_tokens.find_one({"token": qr_token})
                    
                    if not db_token:
                        return {
                            "valid": False,
                            "message": "Token not found or already used"
                        }
                    
                    if db_token.get("used", False):
                        return {
                            "valid": False,
                            "message": "Token already used"
                        }
            
            # Get user details
            db = get_database()
            user = await db.users.find_one({"_id": token_user_id})
            
            if not user:
                return {
                    "valid": False,
                    "message": "User not found"
                }
            
            logger.info(f"✅ QR token verified successfully for user {token_user_id}")
            
            return {
                "valid": True,
                "swap_id": swap_id,
                "user_id": token_user_id,
                "user_name": user.get("name", "Unknown"),
                "message": "Token verified successfully"
            }
        
        except Exception as e:
            logger.error(f"Error verifying QR token: {e}")
            return {
                "valid": False,
                "message": f"Verification error: {str(e)}"
            }
    
    async def mark_token_used(self, qr_token: str) -> bool:
        """Mark QR token as used"""
        try:
            # Remove from Redis
            if self.redis_client:
                await self.redis_client.delete(f"qr_token:{qr_token}")
            
            # Mark as used in MongoDB
            db = get_database()
            result = await db.qr_tokens.update_one(
                {"token": qr_token},
                {
                    "$set": {
                        "used": True,
                        "used_at": datetime.utcnow()
                    }
                }
            )
            
            return result.modified_count > 0
        
        except Exception as e:
            logger.error(f"Error marking token as used: {e}")
            return False


    def generate_qr_image(self, qr_token: str) -> str:
        """
        Generate QR code with logo in center
        Returns base64 encoded PNG
        """

        try:
            # ----------------------------
            # Create QR Code
            # ----------------------------
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_H,  # HIGH for logo
                box_size=10,
                border=1,
            )

            qr.add_data(qr_token)
            qr.make(fit=True)

            qr_img = qr.make_image(
                fill_color="black",
                back_color="white"
            ).convert("RGBA")

            # ----------------------------
            # Load Logo
            # ----------------------------


            logo = Image.open(LOGO_PATH).convert("RGBA")

            # ----------------------------
            # Resize Logo
            # ----------------------------
            qr_width, qr_height = qr_img.size

            logo_size = qr_width // 4   # 25% of QR size
            logo = logo.resize(
                (logo_size, logo_size),
                Image.Resampling.LANCZOS
            )

            # ----------------------------
            # Position Logo (Center)
            # ----------------------------
            pos = (
                (qr_width - logo_size) // 2,
                (qr_height - logo_size) // 2
            )

            # ----------------------------
            # Paste Logo
            # ----------------------------
            qr_img.paste(logo, pos, logo)

            # ----------------------------
            # Save (Optional)
            # ----------------------------
            os.makedirs("generated_qr", exist_ok=True)
            file_path = f"generated_qr/qr_{qr_token[:8]}.png"
            qr_img.save(file_path)

            print("Saved at:", os.path.abspath(file_path))

            # ----------------------------
            # Convert to Base64
            # ----------------------------
            buffer = BytesIO()
            qr_img.save(buffer, format="PNG")

            img_base64 = base64.b64encode(
                buffer.getvalue()
            ).decode()

            return f"data:image/png;base64,{img_base64}"

        except Exception as e:
            print("QR Error:", e)
            return ""

    
    async def cleanup_expired_tokens(self):
        """Clean up expired QR tokens (scheduled task)"""
        try:
            db = get_database()
            
            cutoff_time = datetime.utcnow()
            
            result = await db.qr_tokens.delete_many({
                "expires_at": {"$lt": cutoff_time},
                "used": True
            })
            
            if result.deleted_count > 0:
                logger.info(f"🧹 Cleaned up {result.deleted_count} expired QR tokens")
        
        except Exception as e:
            logger.error(f"Error cleaning up tokens: {e}")


# Global instance
qr_service = QRService()
