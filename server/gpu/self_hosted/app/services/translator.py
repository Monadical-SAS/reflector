import threading


class TextTranslatorService:
    """Simple text-to-text translator using HuggingFace MarianMT models.

    This mirrors the modal translator API shape but uses text translation only.
    """

    def __init__(self):
        self._pipeline = None
        self._lock = threading.Lock()

    def load(self, source_language: str = "en", target_language: str = "fr"):
        from transformers import MarianMTModel, MarianTokenizer, pipeline

        # Pick a default MarianMT model pair if available; fall back to Helsinki-NLP en->fr
        model_name = self._resolve_model_name(source_language, target_language)
        tokenizer = MarianTokenizer.from_pretrained(model_name)
        model = MarianMTModel.from_pretrained(model_name)
        self._pipeline = pipeline("translation", model=model, tokenizer=tokenizer)

    def _resolve_model_name(self, src: str, tgt: str) -> str:
        # Minimal mapping; extend as needed
        pair = (src.lower(), tgt.lower())
        mapping = {
            ("en", "fr"): "Helsinki-NLP/opus-mt-en-fr",
            ("fr", "en"): "Helsinki-NLP/opus-mt-fr-en",
            ("en", "es"): "Helsinki-NLP/opus-mt-en-es",
            ("es", "en"): "Helsinki-NLP/opus-mt-es-en",
            ("en", "de"): "Helsinki-NLP/opus-mt-en-de",
            ("de", "en"): "Helsinki-NLP/opus-mt-de-en",
        }
        return mapping.get(pair, "Helsinki-NLP/opus-mt-en-fr")

    def translate(self, text: str, source_language: str, target_language: str) -> dict:
        if self._pipeline is None:
            self.load(source_language, target_language)
        with self._lock:
            results = self._pipeline(
                text, src_lang=source_language, tgt_lang=target_language
            )
        translated = results[0]["translation_text"] if results else ""
        return {"text": {source_language: text, target_language: translated}}
