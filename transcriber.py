import os
from faster_whisper import WhisperModel

class Transcriber:
    def __init__(self, model_size="tiny", device="cpu", compute_type="int8"):
        """
        Initialize the Whisper model.
        Args:
            model_size: Size of the model (tiny, base, small, medium, large-v2).
            device: 'cuda' for GPU, 'cpu' for CPU.
            compute_type: 'float16' or 'int8_float16' for GPU, 'int8' for CPU.
        """
        print(f"Loading Whisper model: {model_size} on {device}...")
        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
        print("Model loaded successfully.")

    def transcribe(self, audio_data):
        """
        Transcribe audio data. 
        Note: faster-whisper expects a file path or a binary stream.
        For real-time, we might need to handle chunks. 
        For MVP, we'll assume we pass a temporary file path or buffer.
        """
        segments, info = self.model.transcribe(audio_data, beam_size=5)
        
        full_text = ""
        for segment in segments:
            full_text += segment.text + " "
            
        return full_text.strip(), info.language
