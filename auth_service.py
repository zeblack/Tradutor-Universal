from datetime import datetime, timedelta
from typing import Optional
import bcrypt
from jose import JWTError, jwt
from database import Database

# Security configuration
SECRET_KEY = "voicebridge-secret-key-change-in-production-2024"  # TODO: Move to env variable
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

db = Database()

class AuthService:
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        try:
            return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
        except ValueError:
            return False
    
    @staticmethod
    def create_access_token(data: dict) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str) -> Optional[dict]:
        """Verify JWT token and return payload"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except JWTError:
            return None
    
    @staticmethod
    def register_user(email: str, username: str, password: str) -> Optional[dict]:
        """Register a new user"""
        # Validate email format
        if "@" not in email or "." not in email:
            return None
        
        # Validate password strength (minimum 6 characters)
        if len(password) < 6:
            return None
        
        # Hash password
        password_hash = AuthService.hash_password(password)
        
        # Create user in database
        user_id = db.create_user(email, username, password_hash)
        
        if user_id:
            # Create JWT token
            token = AuthService.create_access_token({"user_id": user_id, "email": email})
            return {
                "user_id": user_id,
                "email": email,
                "username": username,
                "token": token
            }
        return None
    
    @staticmethod
    def login_user(email: str, password: str) -> Optional[dict]:
        """Login user and return token"""
        # Get user from database
        user = db.get_user_by_email(email)
        
        if not user:
            return None
        
        # Verify password
        if not AuthService.verify_password(password, user["password_hash"]):
            return None
        
        # Update last login
        db.update_last_login(user["id"])
        
        # Create JWT token
        token = AuthService.create_access_token({"user_id": user["id"], "email": user["email"]})
        
        return {
            "user_id": user["id"],
            "email": user["email"],
            "username": user["username"],
            "token": token
        }
    
    @staticmethod
    def get_current_user(token: str) -> Optional[dict]:
        """Get current user from JWT token"""
        payload = AuthService.verify_token(token)
        
        if not payload:
            return None
        
        user_id = payload.get("user_id")
        if not user_id:
            return None
        
        return db.get_user_by_id(user_id)
