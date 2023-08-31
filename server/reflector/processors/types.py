import io
import tempfile
from pathlib import Path

from pydantic import BaseModel, PrivateAttr


class AudioFile(BaseModel):
    name: str
    sample_rate: int
    channels: int
    sample_width: int
    timestamp: float = 0.0

    _fd: io.BytesIO = PrivateAttr(None)
    _path: Path = PrivateAttr(None)

    def __init__(self, fd, **kwargs):
        super().__init__(**kwargs)
        self._fd = fd

    @property
    def fd(self):
        self._fd.seek(0)
        return self._fd

    @property
    def path(self):
        if self._path is None:
            # write down to disk
            filename = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
            self._path = Path(filename)
            with self._path.open("wb") as f:
                f.write(self._fd.getbuffer())
        return self._path

    def release(self):
        if self._path:
            self._path.unlink()


class Word(BaseModel):
    text: str
    start: float
    end: float


class Transcript(BaseModel):
    text: str = ""
    translation: str | None = None
    words: list[Word] = None

    @property
    def human_timestamp(self):
        minutes = int(self.timestamp / 60)
        seconds = int(self.timestamp % 60)
        milliseconds = int((self.timestamp % 1) * 1000)
        return f"{minutes:02d}:{seconds:02d}.{milliseconds:03d}"

    @property
    def timestamp(self):
        if not self.words:
            raise ValueError("No words in transcript")
        return self.words[0].start

    @property
    def duration(self):
        if not self.words:
            raise ValueError("No words in transcript")
        return self.words[-1].end - self.words[0].start

    def merge(self, other: "Transcript"):
        if not self.words:
            self.words = other.words
        else:
            self.words.extend(other.words)
        self.text += other.text

    def add_offset(self, offset: float):
        for word in self.words:
            word.start += offset
            word.end += offset

    def clone(self):
        words = [
            Word(text=word.text, start=word.start, end=word.end) for word in self.words
        ]
        return Transcript(text=self.text, translation=self.translation, words=words)


class TitleSummary(BaseModel):
    title: str
    summary: str
    timestamp: float
    duration: float
    transcript: Transcript

    @property
    def human_timestamp(self):
        minutes = int(self.timestamp / 60)
        seconds = int(self.timestamp % 60)
        milliseconds = int((self.timestamp % 1) * 1000)
        return f"{minutes:02d}:{seconds:02d}.{milliseconds:03d}"


class FinalSummary(BaseModel):
    summary: str
    duration: float


class FinalTitle(BaseModel):
    title: str


class TranslationLanguages(BaseModel):
    language_to_id_mapping: dict = {
        "Afrikaans": "af",
        "Albanian": "sq",
        "Amharic": "am",
        "Arabic": "ar",
        "Armenian": "hy",
        "Asturian": "ast",
        "Azerbaijani": "az",
        "Bashkir": "ba",
        "Belarusian": "be",
        "Bengali": "bn",
        "Bosnian": "bs",
        "Breton": "br",
        "Bulgarian": "bg",
        "Burmese": "my",
        "Catalan; Valencian": "ca",
        "Cebuano": "ceb",
        "Central Khmer": "km",
        "Chinese": "zh",
        "Croatian": "hr",
        "Czech": "cs",
        "Danish": "da",
        "Dutch; Flemish": "nl",
        "English": "en",
        "Estonian": "et",
        "Finnish": "fi",
        "French": "fr",
        "Fulah": "ff",
        "Gaelic; Scottish Gaelic": "gd",
        "Galician": "gl",
        "Ganda": "lg",
        "Georgian": "ka",
        "German": "de",
        "Greeek": "el",
        "Gujarati": "gu",
        "Haitian; Haitian Creole": "ht",
        "Hausa": "ha",
        "Hebrew": "he",
        "Hindi": "hi",
        "Hungarian": "hu",
        "Icelandic": "is",
        "Igbo": "ig",
        "Iloko": "ilo",
        "Indonesian": "id",
        "Irish": "ga",
        "Italian": "it",
        "Japanese": "ja",
        "Javanese": "jv",
        "Kannada": "kn",
        "Kazakh": "kk",
        "Korean": "ko",
        "Lao": "lo",
        "Latvian": "lv",
        "Lingala": "ln",
        "Lithuanian": "lt",
        "Luxembourgish; Letzeburgesch": "lb",
        "Macedonian": "mk",
        "Malagasy": "mg",
        "Malay": "ms",
        "Malayalam": "ml",
        "Marathi": "mr",
        "Mongolian": "mn",
        "Nepali": "ne",
        "Northern Sotho": "ns",
        "Norwegian": "no",
        "Occitan": "oc",
        "Oriya": "or",
        "Panjabi; Punjabi": "pa",
        "Persian": "fa",
        "Polish": "pl",
        "Portuguese": "pt",
        "Pushto; Pashto": "ps",
        "Romanian; Moldavian; Moldovan": "ro",
        "Russian": "ru",
        "Serbian": "sr",
        "Sindhi": "sd",
        "Sinhala; Sinhalese": "si",
        "Slovak": "sk",
        "Slovenian": "sl",
        "Somali": "so",
        "Spanish": "es",
        "Sundanese": "su",
        "Swahili": "sw",
        "Swati": "ss",
        "Swedish": "sv",
        "Tagalog": "tl",
        "Tamil": "ta",
        "Thai": "th",
        "Tswana": "tn",
        "Turkish": "tr",
        "Ukrainian": "uk",
        "Urdu": "ur",
        "Uzbek": "uz",
        "Vietnamese": "vi",
        "Welsh": "cy",
        "Western Frisian": "fy",
        "Wolof": "wo",
        "Xhosa": "xh",
        "Yiddish": "yi",
        "Yoruba": "yo",
        "Zulu": "zu",
    }

    @property
    def supported_languages(self):
        return self.language_to_id_mapping.values()

    def is_supported(self, lang_id: str) -> bool:
        if lang_id in self.supported_languages:
            return True
        return False
