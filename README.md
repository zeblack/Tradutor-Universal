# VoiceBridge 🌐🎙️

> Real-time multilingual voice translation platform with screen sharing capabilities

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![Redis](https://img.shields.io/badge/Redis-7.0+-red.svg)](https://redis.io/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

VoiceBridge is a powerful real-time translation platform that enables seamless multilingual communication through voice, text, and screen sharing. Built with FastAPI, WebRTC, and Redis for scalability and performance.

![VoiceBridge Demo](https://via.placeholder.com/800x400/667eea/ffffff?text=VoiceBridge+Demo)

## ✨ Features

### 🎯 Core Features
- **Real-time Translation** - Instant voice and text translation across 8+ languages
- **Screen Sharing** - WebRTC-powered screen sharing with late-join support
- **Multi-User Rooms** - Public and private rooms with password protection
- **Session Persistence** - Auto-reconnect on page refresh
- **Multi-Device Support** - Same user across multiple tabs/devices

### 🌍 Supported Languages
- 🇧🇷 Portuguese (pt-BR)
- 🇺🇸 English (en-US)
- 🇪🇸 Spanish (es-ES)
- 🇫🇷 French (fr-FR)
- 🇩🇪 German (de-DE)
- 🇮🇹 Italian (it-IT)
- 🇯🇵 Japanese (ja-JP)
- 🇨🇳 Chinese (zh-CN)

### 🔧 Technical Features
- **WebRTC P2P** - Low-latency peer-to-peer connections
- **Redis Persistence** - Scalable room and session management
- **JWT Authentication** - Secure user authentication
- **Speech-to-Text** - Browser-based speech recognition
- **Text-to-Speech** - EdgeTTS for natural voice synthesis
- **Avatar System** - Custom user avatars with image upload

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Redis 7.0+
- Modern web browser (Chrome/Edge recommended)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/voicebridge.git
cd voicebridge
```

2. **Create virtual environment**
```bash
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Start Redis** (Docker)
```bash
docker run -d --name vb-redis -p 6379:6379 redis
```

5. **Run the application**
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

6. **Access the app**
```
http://localhost:8000
```

## 📁 Project Structure

```
voicebridge/
├── main.py                 # FastAPI application & WebSocket handler
├── auth_service.py         # JWT authentication service
├── translator_service.py   # Google Translate integration
├── tts_service.py         # EdgeTTS service
├── database.py            # SQLite database manager
├── requirements.txt       # Python dependencies
├── static/
│   ├── discord.html       # Main chat interface
│   ├── login.html         # Login/Register page
│   ├── profile.html       # User profile page
│   ├── style.css          # Global styles
│   └── webrtc_screen_share.js  # WebRTC module
├── audio_output/          # Generated TTS files
├── avatars/               # User avatar uploads
└── voicebridge.db         # SQLite database
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file (optional):

```env
REDIS_URL=redis://localhost:6379
JWT_SECRET=your-secret-key-here
DATABASE_URL=sqlite:///./voicebridge.db
```

### Redis Configuration

Default connection: `redis://localhost:6379`

To use a different Redis instance:
```python
# main.py
redis_client = redis.from_url("redis://your-redis-host:6379")
```

## 📖 Usage

### Creating a Room

1. Login or register an account
2. Click "Create Room" tab
3. Enter room name
4. Choose Public or Private
5. Click "Initialize Room"

### Joining a Room

**Public Room:**
- Select from the room list
- Click to join

**Private Room:**
- Enter room code
- Enter password (if required)
- Click "Join"

### Screen Sharing

1. Click the 📺 button in the sidebar
2. Select window/screen to share
3. Other participants see your screen automatically
4. Late joiners are automatically connected

### Translation

**Voice Input:**
- Click 🎤 button to start dictation
- Speak in your language
- Translation sent to all participants

**Text Input:**
- Type message in chat box
- Press Enter or click ➤
- Auto-translated for each participant

## 🏗️ Architecture

### Backend Stack
- **FastAPI** - High-performance async web framework
- **Redis** - Room persistence and pub/sub
- **SQLite** - User data and session tracking
- **WebSockets** - Real-time bidirectional communication

### Frontend Stack
- **Vanilla JavaScript** - No framework dependencies
- **WebRTC** - Peer-to-peer screen sharing
- **Web Speech API** - Browser-based STT
- **SessionStorage** - Client-side persistence

### Translation Pipeline
```
User Input → Speech Recognition → Translation → TTS → Audio Playback
     ↓              ↓                  ↓          ↓         ↓
  Browser      Web Speech API    Google Trans  EdgeTTS   Browser
```

## 🔐 Security

- **JWT Authentication** - Secure token-based auth
- **Password Hashing** - bcrypt for user passwords
- **Room Passwords** - Optional password protection
- **CORS** - Configured for production
- **Input Validation** - Pydantic models

## 🧪 Testing

### Manual Testing Checklist

- [ ] Create account and login
- [ ] Create public room
- [ ] Create private room with password
- [ ] Join room with different account
- [ ] Send text message
- [ ] Use voice dictation
- [ ] Start screen sharing
- [ ] Join room during active presentation
- [ ] Refresh page (session persistence)
- [ ] Multiple tabs same account

## 🐛 Troubleshooting

### Common Issues

**Redis Connection Failed**
```bash
# Start Redis
docker start vb-redis
# Or install locally
```

**WebRTC Not Working**
- Use HTTPS in production
- Check firewall settings
- Verify STUN server access

**Audio Not Playing**
- Check browser permissions
- Verify EdgeTTS installation
- Check audio output folder

**Screen Sharing Not Visible**
- Ensure both users in same room
- Check browser console for errors
- Verify WebRTC peer connection

## 🚀 Deployment

### Production Checklist

1. **Environment Variables**
```bash
export REDIS_URL=redis://production-redis:6379
export JWT_SECRET=strong-random-secret
```

2. **HTTPS Setup**
```bash
# Use reverse proxy (nginx/caddy)
# WebRTC requires HTTPS in production
```

3. **Redis Persistence**
```bash
# Configure Redis persistence
docker run -d -v redis-data:/data redis redis-server --appendonly yes
```

4. **Process Manager**
```bash
# Use gunicorn or uvicorn with workers
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker
```

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Google Translate** - Translation API
- **EdgeTTS** - Text-to-speech synthesis
- **FastAPI** - Web framework
- **Redis** - Data persistence
- **WebRTC** - Real-time communication

## 📧 Contact

- **Author:** Your Name
- **Email:** your.email@example.com
- **GitHub:** [@yourusername](https://github.com/yourusername)
- **Project Link:** [https://github.com/yourusername/voicebridge](https://github.com/yourusername/voicebridge)

## 🗺️ Roadmap

- [ ] Mobile app (React Native)
- [ ] Recording functionality
- [ ] Chat history persistence
- [ ] Room analytics dashboard
- [ ] TURN server integration
- [ ] End-to-end encryption
- [ ] AI-powered translation improvements
- [ ] Video conferencing support

---

**Made with ❤️ by the VoiceBridge Team**
