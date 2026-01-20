import asyncio
from tts_service import TTSService
import os

async def main():
    print("Testing TTS Service...")
    tts = TTSService()
    try:
        path = await tts.generate_audio("Hello, this is a test of the translation system.", lang="en")
        print(f"Audio generated at: {path}")
        if path and os.path.exists(path):
            print(f"File size: {os.path.getsize(path)} bytes")
        else:
            print("File not found!")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
