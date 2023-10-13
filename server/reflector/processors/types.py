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


class FinalLongSummary(BaseModel):
    long_summary: str
    duration: float


class FinalShortSummary(BaseModel):
    short_summary: str
    duration: float


class FinalTitle(BaseModel):
    title: str


# https://github.com/facebookresearch/seamless_communication/tree/main/scripts/m4t/predict#supported-languages
class TranslationLanguages(BaseModel):
    language_to_id_mapping: dict = {
        "afr": "Afrikaans",
        "azj": "North Azerbaijani",
        "bos": "Bosnian",
        "cat": "Catalan",
        "ceb": "Cebuano",
        "ces": "Czech",
        "cym": "Welsh",
        "dan": "Danish",
        "deu": "German",
        "eng": "English",
        "est": "Estonian",
        "eus": "Basque",
        "fin": "Finnish",
        "fra": "French",
        "gaz": "West Central Oromo",
        "gle": "Irish",
        "glg": "Galician",
        "hrv": "Croatian",
        "hun": "Hungarian",
        "ibo": "Igbo",
        "ind": "Indonesian",
        "isl": "Icelandic",
        "ita": "Italian",
        "jav": "Javanese",
        "lit": "Lithuanian",
        "lug": "Ganda",
        "luo": "Luo",
        "lvs": "Standard Latvian",
        "mlt": "Maltese",
        "nld": "Dutch",
        "nno": "Norwegian Nynorsk",
        "nob": "Norwegian Bokmål",
        "nya": "Nyanja",
        "pol": "Polish",
        "por": "Portuguese",
        "ron": "Romanian",
        "slk": "Slovak",
        "slv": "Slovenian",
        "sna": "Shona",
        "som": "Somali",
        "spa": "Spanish",
        "swe": "Swedish",
        "swh": "Swahili",
        "tgl": "Tagalog",
        "tur": "Turkish",
        "uzn": "Northern Uzbek",
        "vie": "Vietnamese",
        "yor": "Yoruba",
        "zsm": "Standard Malay",
        "zul": "Zulu",
    }

    @property
    def supported_languages(self):
        return self.language_to_id_mapping.keys()

    def is_supported(self, lang_id: str) -> bool:
        if lang_id in self.supported_languages:
            return True
        return False
