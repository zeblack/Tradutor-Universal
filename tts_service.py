import edge_tts
import tempfile
import os

class TTSService:
    def __init__(self):
        # Mapping simple language codes to specific Edge-TTS voices
        self.voices = {
            'en': 'en-US-ChristopherNeural',
            'pt': 'pt-BR-AntonioNeural',
            'es': 'es-ES-AlvaroNeural',
            'fr': 'fr-FR-HenriNeural',
            'de': 'de-DE-ConradNeural',
            'it': 'it-IT-IsabellaNeural',
            'ja': 'ja-JP-NanamiNeural',
            'zh-CN': 'zh-CN-XiaoxiaoNeural'
        }

    async def generate_audio(self, text, lang='en'):
        """
        Generates audio from text and returns the file path.
        """
        if not text:
            return None
            
        voice = self.voices.get(lang, 'en-US-ChristopherNeural')
        communicate = edge_tts.Communicate(text, voice)
        
        # Create a temporary file
        fd, path = tempfile.mkstemp(suffix=".mp3")
        os.close(fd) # Close the file descriptor, we just needed the path
        
        await communicate.save(path)
        return path
