from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Header, File, UploadFile, Query
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
import shutil
import os
import io
import asyncio
from PIL import Image
import uuid
import json
from typing import Dict, Set, Optional
from dataclasses import dataclass

from translator_service import TranslationService
from tts_service import TTSService
from auth_service import AuthService
from database import Database

import redis.asyncio as aioredis

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")
os.makedirs("audio_output", exist_ok=True)
app.mount("/audio", StaticFiles(directory="audio_output"), name="audio")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Services
translator = TranslationService()
tts = TTSService()
auth = AuthService()
db = Database()

# Redis for room persistence only
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
try:
    redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)
    print(f"Services initialized (Translator + TTS + Auth + Redis at {REDIS_URL}).")
except:
    redis_client = None
    print("Services initialized (Translator + TTS + Auth). Redis not available.")

# Room Management
@dataclass
class Room:
    id: str
    name: str
    users: Dict[str, 'User']
    is_public: bool = True
    password: str = None
    created_by: str = None
    active_presenter: str = None  # Track who is presenting

@dataclass
class User:
    websocket: WebSocket
    connection_id: str  # Unique per WebSocket connection
    user_id: str        # Account ID (can be same across connections)
    language: str 
    name: str
    room_id: str
    role: str = "speaker"
    avatar_url: str = None
    session_id: int = None

# Global Rooms storage
# rooms[room_id].users is now keyed by connection_id, not user_id
rooms: Dict[str, Room] = {}

class ConnectionManager:
    # Helper to manage broadcasting interactions
    pass

# Pydantic Models for Auth
class RegisterRequest(BaseModel):
    email: EmailStr
    username: str
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

from fastapi.responses import RedirectResponse

@app.get("/")
async def get():
    return RedirectResponse(url="/static/login.html")

# Authentication Endpoints
@app.post("/api/auth/register")
async def register(request: RegisterRequest):
    """Register a new user"""
    result = auth.register_user(request.email, request.username, request.password)
    
    if not result:
        raise HTTPException(status_code=400, detail="Email already exists or invalid data")
    
    return {
        "success": True,
        "user": {
            "id": result["user_id"],
            "email": result["email"],
            "username": result["username"]
        },
        "token": result["token"]
    }

@app.post("/api/auth/login")
async def login(request: LoginRequest):
    """Login user"""
    result = auth.login_user(request.email, request.password)
    
    if not result:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    return {
        "success": True,
        "user": {
            "id": result["user_id"],
            "email": result["email"],
            "username": result["username"],
            "avatar_url": result.get("avatar_url")
        },
        "token": result["token"]
    }

@app.get("/api/auth/me")
async def get_current_user_info(authorization: Optional[str] = Header(None)):
    """Get current user info from JWT token"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.replace("Bearer ", "")
    user = auth.get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return {"user": user}

@app.get("/api/auth/history")
async def get_room_history(authorization: Optional[str] = Header(None)):
    """Get user's room history"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.replace("Bearer ", "")
    user = auth.get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    history = db.get_user_room_history(user["id"])
    return {"history": history}

@app.post("/api/profile/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    authorization: str = Header(None)
):
    """Upload user avatar"""
    # Verify auth
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.replace("Bearer ", "")
    user = auth.get_current_user(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Validate file type
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Read and resize image
    contents = await file.read()
    try:
        image = Image.open(io.BytesIO(contents))
        
        # Resize to 256x256
        image.thumbnail((256, 256))
        
        # Save with unique filename
        filename = f"avatar_{user['id']}_{uuid.uuid4()}.png"
        filepath = f"static/avatars/{filename}"
        os.makedirs("static/avatars", exist_ok=True)
        image.save(filepath, "PNG")
        
        # Update database
        avatar_url = f"/static/avatars/{filename}"
        db.update_user_avatar(user["id"], avatar_url)
        
        return {"avatar_url": avatar_url}
    except Exception as e:
        print(f"Error uploading avatar: {e}")
        raise HTTPException(status_code=500, detail="Failed to process image")

# Helper Functions for Broadcasting
async def broadcast_participant_list(room_id: str):
    """Send updated participant list to all users in a room"""
    if room_id not in rooms:
        return
    
    room = rooms[room_id]
    participants = []
    
    for user in room.users.values():
        participants.append({
            "id": user.user_id,
            "name": user.name,
            "language": user.language,
            "role": user.role,
            "avatar_url": user.avatar_url
        })
    
    # Broadcast to all users in the room
    for user in room.users.values():
        try:
            await user.websocket.send_json({
                "type": "participants",
                "participants": participants
            })
        except:
            pass

async def broadcast_system_message(room_id: str, message: str, exclude_user: str = None):
    """Send a system message to all users in a room"""
    if room_id not in rooms:
        return
    
    for user in rooms[room_id].users.values():
        if exclude_user and user.user_id == exclude_user:
            continue
        try:
            await user.websocket.send_json({
                "type": "system",
                "message": message
            })
        except:
            pass

async def broadcast_translation(room_id: str, sender: User, original_text: str, source_lang: str):
    """Translate and broadcast message to all users IN THE ROOM"""
    if room_id not in rooms: return
    
    active_users = rooms[room_id].users
    
    # Map browser lang codes to translator codes
    lang_map = {
        'pt-BR': 'pt', 'pt-PT': 'pt',
        'en-US': 'en', 'en-GB': 'en',
        'es-ES': 'es', 'es-MX': 'es',
        'fr-FR': 'fr', 'de-DE': 'de',
        'it-IT': 'it', 'ja-JP': 'ja',
        'zh-CN': 'zh-CN', 'ko-KR': 'ko'
    }
    
    source_lang_clean = lang_map.get(source_lang, source_lang.split('-')[0])
    
    # Group users by target language
    users_by_language = {}
    for user_id, user in active_users.items():
        target_lang_clean = lang_map.get(user.language, user.language.split('-')[0])
        if target_lang_clean not in users_by_language:
            users_by_language[target_lang_clean] = []
        users_by_language[target_lang_clean].append(user)
    
    print(f"[{room_id}] 💾 Generating {len(users_by_language)} audio files")
    
    language_data = {}
    
    for target_lang_clean, users_in_lang in users_by_language.items():
        try:
            # Translate
            if source_lang_clean == target_lang_clean:
                translated_text = original_text
                print(f"    ✓ {target_lang_clean}: No translation needed (same language)")
            else:
                print(f"    🔄 Translating {source_lang_clean} -> {target_lang_clean}...")
                translated_text = await translator.translate(
                    original_text, 
                    source_lang=source_lang_clean, 
                    target_lang=target_lang_clean
                )
                print(f"    ✓ {target_lang_clean}: \"{translated_text}\"")
            
            # TTS
            audio_path = await tts.generate_audio(translated_text, lang=target_lang_clean)
            audio_url = None
            if audio_path:
                public_filename = f"tts_{room_id}_{target_lang_clean}_{uuid.uuid4()}.mp3"
                shutil.move(audio_path, os.path.join("audio_output", public_filename))
                audio_url = f"/audio/{public_filename}"
            
            language_data[target_lang_clean] = {
                "translated_text": translated_text,
                "audio_url": audio_url
            }
            
        except Exception as e:
            print(f"    ❌ Error processing {target_lang_clean}: {e}")
            import traceback
            traceback.print_exc()
            language_data[target_lang_clean] = {"translated_text": original_text, "audio_url": None}
    
    # Send
    for target_lang_clean, users_in_lang in users_by_language.items():
        data = language_data.get(target_lang_clean)
        if not data: continue
            
        for user in users_in_lang:
            try:
                is_sender = user.user_id == sender.user_id
                response = {
                    "type": "message",
                    "sender_id": sender.user_id,
                    "sender_name": sender.name,
                    "sender_lang": source_lang,
                    "original_text": original_text,
                    "translated_text": data["translated_text"],
                    "target_lang": user.language,
                    "audio_url": data["audio_url"],
                    "is_self": is_sender,
                    "room_id": room_id
                }
                print(f"    📤 Sending to {user.name} (is_self={is_sender})")
                await user.websocket.send_json(response)
            except: pass

@app.get("/api/rooms")
async def list_rooms():
    """List functional public rooms for the lobby"""
    public_rooms = []
    
    # Try Redis first for cross-process visibility
    if redis_client:
        try:
            room_ids = await redis_client.smembers("rooms:public")
            for rid in room_ids:
                r_data = await redis_client.hgetall(f"rooms:{rid}")
                if r_data:
                    # Count users from in-memory if room exists locally
                    u_count = len(rooms[rid].users) if rid in rooms else 0
                    public_rooms.append({
                        "id": rid,
                        "name": r_data.get("name", "Untitled Room"),
                        "users_count": u_count,
                        "has_password": r_data.get("password") != ""
                    })
            return {"rooms": public_rooms}
        except Exception as e:
            print(f"Redis fetch error: {e}")
    
    # Fallback to in-memory
    for r in rooms.values():
        if r.is_public:
            public_rooms.append({
                "id": r.id,
                "name": r.name,
                "users_count": len(r.users),
                "has_password": bool(r.password)
            })
    return {"rooms": public_rooms}

@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None)
):
    await websocket.accept()
    
    # 1. Authentication
    authenticated_user = None
    if token:
        authenticated_user = auth.get_current_user(token)
    
    if authenticated_user:
        user_id = str(authenticated_user["id"])
        base_name = authenticated_user["username"]
        user_avatar = authenticated_user.get("avatar_url")
    else:
        user_id = f"guest_{str(uuid.uuid4())[:8]}"
        base_name = f"Guest-{user_id[-4:]}"
        user_avatar = None

    user = None
    room_id = None
    
    try:
        print(f"🔌 New WebSocket connection from {websocket.client} (Auth: {bool(authenticated_user)})")
        
        # Wait for initial handshake
        init_data = await websocket.receive_text()
        init_msg = json.loads(init_data)
        
        # User metadata from handshake overrides DB name if needed, but let's prefer DB name if auth
        user_lang = init_msg.get("language", "en")
        user_name = base_name 
        if not authenticated_user and init_msg.get("name"):
             user_name = init_msg.get("name")
        
        user_role = init_msg.get("role", "speaker")
        
        # Room connection params
        req_room_id = init_msg.get("room_id", "").strip().upper()
        req_room_name = init_msg.get("room_name", "Untitled Room")
        req_password = init_msg.get("password", "")
        req_is_public = init_msg.get("is_public", True)
        
        # Room Logic
        if not req_room_id or req_room_id == "CREATE":
            # Create new room
            room_id = str(uuid.uuid4())[:6].upper()
            new_room = Room(
                id=room_id,
                name=req_room_name,
                users={},
                is_public=req_is_public,
                password=req_password if req_password else None,
                created_by=user_id
            )
            rooms[room_id] = new_room
            
            # Sync with Redis
            if redis_client:
                try:
                    await redis_client.hset(f"rooms:{room_id}", mapping={
                        "id": room_id,
                        "name": req_room_name,
                        "is_public": str(req_is_public),
                        "password": req_password if req_password else "",
                        "created_by": user_id
                    })
                    if req_is_public:
                        await redis_client.sadd("rooms:public", room_id)
                except Exception as e:
                    print(f"Redis sync error: {e}")
            
            print(f"🏠 Created new room: {room_id} ({req_room_name})")
            
        else:
            # Join existing
            room_id = req_room_id
            
            # Auto-create if not exists
            if room_id not in rooms:
                new_room = Room(
                    id=room_id,
                    name=f"Room {room_id}",
                    users={},
                    is_public=req_is_public,  # Use the requested public flag
                    password=req_password if req_password else None
                )
                rooms[room_id] = new_room
                
                # Sync with Redis
                if redis_client:
                    try:
                        await redis_client.hset(f"rooms:{room_id}", mapping={
                            "id": room_id,
                            "name": f"Room {room_id}",
                            "is_public": str(req_is_public),
                            "password": req_password if req_password else "",
                            "created_by": ""
                        })
                        if req_is_public:
                            await redis_client.sadd("rooms:public", room_id)
                    except Exception as e:
                        print(f"Redis sync error: {e}")
            
            # Password check
            room = rooms[room_id]
            if room.password and room.password != req_password:
                await websocket.send_json({"type": "error", "message": "Invalid Password"})
                await websocket.close()
                return
        
        # Create user object with unique connection_id
        connection_id = str(uuid.uuid4())
        user = User(
            websocket=websocket,
            connection_id=connection_id,
            user_id=user_id,
            language=user_lang,
            name=user_name,
            room_id=room_id,
            role=user_role,
            avatar_url=user_avatar
        )
        
        rooms[room_id].users[connection_id] = user  # Key by connection_id, not user_id
        room_obj = rooms[room_id]
        print(f"✅ {user_name} joined Room {room_id} (ID: {user_id}, Conn: {connection_id[:8]})")

        # 2. Track Session
        if authenticated_user:
            try:
                session_id = db.create_room_session(
                    user_id=authenticated_user["id"],
                    room_id=room_id,
                    room_name=room_obj.name,
                    role=user_role
                )
                user.session_id = session_id
            except Exception as e:
                print(f"Error creating session: {e}")
        
        # Send ROOM INFO back to user
        await websocket.send_json({
            "type": "room_joined",
            "room_id": room_id,
            "room_name": room_obj.name,
            "message": f"Joined {room_obj.name}",
            "user_name": user_name,
            "user_id": user_id
        })
        
        # Notify about active presentation if any (late-join support)
        if room_obj.active_presenter and room_obj.active_presenter != user_id:
            # Find presenter connection
            presenter_user = None
            for conn_id, u in rooms[room_id].users.items():
                if u.user_id == room_obj.active_presenter:
                    presenter_user = u
                    break
            
            if presenter_user:
                # Notify viewer about presentation
                await websocket.send_json({
                    "type": "presentation_started",
                    "presenter_id": room_obj.active_presenter,
                    "presenter_name": presenter_user.name
                })
                print(f"📺 Notified {user_name} about ongoing presentation by {presenter_user.name}")
                
                # Notify presenter about new viewer (so they can send offer)
                await presenter_user.websocket.send_json({
                    "type": "new_viewer",
                    "viewer_id": user_id,
                    "viewer_name": user_name
                })
                print(f"👁️ Notified presenter {presenter_user.name} about new viewer {user_name}")
        
        # Notify room
        await broadcast_system_message(room_id, f"{user_name} joined the room", exclude_user=None)
        await broadcast_participant_list(room_id)
        
        # Main message loop
        while True:
            data_json = await websocket.receive_text()
            data = json.loads(data_json)
            
            message_type = data.get("type", "speech")
            
            if message_type == "speech":
                original_text = data.get("text", "")
                if not original_text.strip(): continue
                
                print(f"🎤 [{room_id}] {user_name}: {original_text}")
                await broadcast_translation(room_id, user, original_text, user.language)
            
            elif message_type in ["signal_offer", "signal_answer", "signal_ice"]:
                # WebRTC signaling - find target by user_id
                target_user_id = data.get("target")
                if target_user_id and room_id in rooms:
                    # Find the target user's connection(s)
                    for conn_id, room_user in rooms[room_id].users.items():
                        if room_user.user_id == target_user_id:
                            data["sender"] = user_id
                            try:
                                await room_user.websocket.send_json(data)
                                print(f"📡 WebRTC signal sent: {message_type} from {user_id} to {target_user_id}")
                            except Exception as e:
                                print(f"Error sending WebRTC signal: {e}")
                            break  # Send to first matching connection
            
            elif message_type == "start_presentation":
                # Track active presenter
                rooms[room_id].active_presenter = user_id
                
                await broadcast_system_message(room_id, f"📺 {user_name} started presenting", exclude_user=None)
                for u in rooms[room_id].users.values():
                     if u.user_id != user_id:
                        await u.websocket.send_json({
                            "type": "presentation_started",
                            "presenter_id": user_id,
                            "presenter_name": user_name
                        })

            elif message_type == "stop_presentation":
                # Clear active presenter
                rooms[room_id].active_presenter = None
                
                for u in rooms[room_id].users.values():
                    await u.websocket.send_json({
                        "type": "presentation_stopped",
                        "presenter_id": user_id
                    })
    
    except WebSocketDisconnect:
        print(f"❌ {user_name if user else user_id} disconnected")
    except Exception as e:
        print(f"Error for user {user_id}: {e}")
    finally:
        # 3. End Session
        if user and user.session_id:
             try:
                 db.end_room_session(user.session_id)
             except Exception as e:
                 print(f"Error ending session: {e}")

        if room_id and room_id in rooms:
            # Find and remove this specific connection
            connection_to_remove = None
            for conn_id, room_user in rooms[room_id].users.items():
                if room_user.websocket == websocket:
                    connection_to_remove = conn_id
                    break
            
            if connection_to_remove:
                del rooms[room_id].users[connection_to_remove]
                print(f"🗑️ Removed {user_name if 'user_name' in locals() else user_id} from Room {room_id} (Conn: {connection_to_remove[:8]})")
            
            if not rooms[room_id].users:
                # Delete from both in-memory and Redis
                del rooms[room_id]
                if redis_client:
                    try:
                        await redis_client.delete(f"rooms:{room_id}")
                        await redis_client.srem("rooms:public", room_id)
                    except Exception as e:
                        print(f"Redis cleanup error: {e}")
                print(f"🗑️ Room {room_id} deleted (empty)")
            else:
                # Broadcast updates to remaining users
                if user and user.name:
                    await broadcast_system_message(room_id, f"{user.name} left the room", exclude_user=user_id)
                await broadcast_participant_list(room_id)
                print(f"📢 Broadcasted participant list update for room {room_id}")
