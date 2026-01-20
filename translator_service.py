from deep_translator import GoogleTranslator

class TranslationService:
    def __init__(self):
        # Supported language codes for deep-translator
        self.supported_langs = {
            'pt': 'portuguese',
            'en': 'english',
            'es': 'spanish',
            'fr': 'french',
            'de': 'german',
            'it': 'italian',
            'ja': 'japanese',
            'zh-CN': 'chinese (simplified)',
            'ko': 'korean'
        }

    async def translate(self, text, source_lang='auto', target_lang='en'):
        """
        Translate text from source to target language using deep-translator.
        """
        if not text or not text.strip():
            return ""
            
        try:
            print(f"🔤 Translating: '{text}' from {source_lang} to {target_lang}")
            
            translator = GoogleTranslator(source=source_lang, target=target_lang)
            result = translator.translate(text)
            
            print(f"✅ Translation result: '{result}'")
            return result
            
        except Exception as e:
            print(f"❌ Translation error ({source_lang}->{target_lang}): {e}")
            return text  # Fallback to original text
