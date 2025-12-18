import io
import re
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Annotated, TypedDict

from pydantic import BaseModel, Field, PrivateAttr


class DiarizationSegment(TypedDict):
    """Type definition for diarization segment containing speaker information"""

    start: float
    end: float
    speaker: int


PUNC_RE = re.compile(r"[.;:?!…]")
SENTENCE_END_RE = re.compile(r"[.?!…]$")

# Max segment length for words_to_segments() - breaks on any punctuation (. ; : ? ! …)
# when segment exceeds this limit. Used for non-multitrack recordings.
MAX_SEGMENT_CHARS = 120

# Max segment length for words_to_segments_by_sentence() - only breaks on sentence-ending
# punctuation (. ? ! …) when segment exceeds this limit. Higher threshold allows complete
# sentences in multitrack recordings where speakers overlap.
# similar number to server/reflector/processors/transcript_liner.py
MAX_SENTENCE_SEGMENT_CHARS = 1000


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


# non-negative seconds with float part
Seconds = Annotated[float, Field(ge=0.0, description="Time in seconds with float part")]


class Word(BaseModel):
    text: str
    start: Seconds
    end: Seconds
    speaker: int = 0


class TranscriptSegment(BaseModel):
    text: str
    start: Seconds
    end: Seconds
    speaker: int = 0


def words_to_segments(words: list[Word]) -> list[TranscriptSegment]:
    # from a list of word, create a list of segments
    # join the word that are less than 2 seconds apart
    # but separate if the speaker changes, or if the punctuation is a . , ; : ? !
    segments = []
    current_segment = None

    for word in words:
        if current_segment is None:
            current_segment = TranscriptSegment(
                text=word.text,
                start=word.start,
                end=word.end,
                speaker=word.speaker,
            )
            continue

        # If the word is attach to another speaker, push the current segment
        # and start a new one
        if word.speaker != current_segment.speaker:
            segments.append(current_segment)
            current_segment = TranscriptSegment(
                text=word.text,
                start=word.start,
                end=word.end,
                speaker=word.speaker,
            )
            continue

        # if the word is the end of a sentence, and we have enough content,
        # add the word to the current segment and push it
        current_segment.text += word.text
        current_segment.end = word.end

        have_punc = PUNC_RE.search(word.text)
        if have_punc and (len(current_segment.text) > MAX_SEGMENT_CHARS):
            segments.append(current_segment)
            current_segment = None

    if current_segment:
        segments.append(current_segment)

    return segments


def words_to_segments_by_sentence(words: list[Word]) -> list[TranscriptSegment]:
    """Group words by speaker, then split into sentences.

    For multitrack recordings where words from different speakers are interleaved
    by timestamp, this function first groups all words by speaker, then creates
    segments based on sentence boundaries within each speaker's words.

    This produces cleaner output than words_to_segments() which breaks on every
    speaker change, resulting in many tiny segments when speakers overlap.
    """
    if not words:
        return []

    # Group words by speaker, preserving order within each speaker
    by_speaker: dict[int, list[Word]] = defaultdict(list)
    for w in words:
        by_speaker[w.speaker].append(w)

    segments: list[TranscriptSegment] = []

    for speaker, speaker_words in by_speaker.items():
        current_text = ""
        current_start: float | None = None
        current_end: float = 0.0

        for word in speaker_words:
            if current_start is None:
                current_start = word.start

            current_text += word.text
            current_end = word.end

            # Check for sentence end or max length
            is_sentence_end = SENTENCE_END_RE.search(word.text.strip())
            is_too_long = len(current_text) >= MAX_SENTENCE_SEGMENT_CHARS

            if is_sentence_end or is_too_long:
                segments.append(
                    TranscriptSegment(
                        text=current_text,
                        start=current_start,
                        end=current_end,
                        speaker=speaker,
                    )
                )
                current_text = ""
                current_start = None

        # Flush remaining words for this speaker
        if current_text and current_start is not None:
            segments.append(
                TranscriptSegment(
                    text=current_text,
                    start=current_start,
                    end=current_end,
                    speaker=speaker,
                )
            )

    # Sort segments by start time
    segments.sort(key=lambda s: s.start)
    return segments


class Transcript(BaseModel):
    translation: str | None = None
    words: list[Word] = []

    @property
    def text(self):
        return "".join([word.text for word in self.words])

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

    def add_offset(self, offset: float):
        for word in self.words:
            word.start += offset
            word.end += offset

    def as_segments(self, is_multitrack: bool = False) -> list[TranscriptSegment]:
        if is_multitrack:
            return words_to_segments_by_sentence(self.words)
        return words_to_segments(self.words)


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


class TitleSummaryWithId(TitleSummary):
    id: str


class FinalLongSummary(BaseModel):
    long_summary: str
    duration: float


class FinalShortSummary(BaseModel):
    short_summary: str
    duration: float


class ActionItems(BaseModel):
    action_items: dict  # JSON-serializable dict from ActionItemsResponse


class FinalTitle(BaseModel):
    title: str


# https://github.com/facebookresearch/seamless_communication/tree/main/scripts/m4t/predict#supported-languages
class TranslationLanguages(BaseModel):
    language_to_id_mapping: dict = {
        # Afrikaans
        "af": "afr",
        # Amharic
        "am": "amh",
        # Modern Standard Arabic
        "ar": "arb",
        # Moroccan Arabic
        "ary": "ary",
        # Egyptian Arabic
        "arz": "arz",
        # Assamese
        "as": "asm",
        # North Azerbaijani
        "az": "azj",
        # Belarusian
        "be": "bel",
        # Bengali
        "bn": "ben",
        # Bosnian
        "bs": "bos",
        # Bulgarian
        "bg": "bul",
        # Catalan
        "ca": "cat",
        # Cebuano
        "ceb": "ceb",
        # Czech
        "cs": "ces",
        # Central Kurdish
        "ku": "ckb",
        # Mandarin Chinese
        "cmn": "cmn_Hant",
        # Welsh
        "cy": "cym",
        # Danish
        "da": "dan",
        # German
        "de": "deu",
        # Greek
        "el": "ell",
        # English
        "en": "eng",
        # Estonian
        "et": "est",
        # Basque
        "eu": "eus",
        # Finnish
        "fi": "fin",
        # French
        "fr": "fra",
        # Irish
        "ga": "gle",
        # West Central Oromo,
        "gaz": "gaz",
        # Galician
        "gl": "glg",
        # Gujarati
        "gu": "guj",
        # Hebrew
        "he": "heb",
        # Hindi
        "hi": "hin",
        # Croatian
        "hr": "hrv",
        # Hungarian
        "hu": "hun",
        # Armenian
        "hy": "hye",
        # Igbo
        "ig": "ibo",
        # Indonesian
        "id": "ind",
        # Icelandic
        "is": "isl",
        # Italian
        "it": "ita",
        # Javanese
        "jv": "jav",
        # Japanese
        "ja": "jpn",
        # Kannada
        "kn": "kan",
        # Georgian
        "ka": "kat",
        # Kazakh
        "kk": "kaz",
        # Halh Mongolian
        "khk": "khk",
        # Khmer
        "km": "khm",
        # Kyrgyz
        "ky": "kir",
        # Korean
        "ko": "kor",
        # Lao
        "lo": "lao",
        # Lithuanian
        "lt": "lit",
        # Ganda
        "lg": "lug",
        # Luo
        "luo": "luo",
        # Standard Latvian
        "lv": "lvs",
        # Maithili
        "mai": "mai",
        # Malayalam
        "ml": "mal",
        # Marathi
        "mr": "mar",
        # Macedonian
        "mk": "mkd",
        # Maltese
        "mt": "mlt",
        # Meitei
        "mni": "mni",
        # Burmese
        "my": "mya",
        # Dutch
        "nl": "nld",
        # Norwegian Nynorsk
        "nn": "nno",
        # Norwegian Bokmål
        "nb": "nob",
        # Nepali
        "ne": "npi",
        # Nyanja
        "ny": "nya",
        # Odia
        "or": "ory",
        # Punjabi
        "pa": "pan",
        # Southern Pashto
        "pbt": "pbt",
        # Western Persian
        "pes": "pes",
        # Polish
        "pl": "pol",
        # Portuguese
        "pt": "por",
        # Romanian
        "ro": "ron",
        # Russian
        "ru": "rus",
        # Slovak
        "sk": "slk",
        # Slovenian
        "sl": "slv",
        # Shona
        "sn": "sna",
        # Sindhi
        "sd": "snd",
        # Somali
        "so": "som",
        # Spanish
        "es": "spa",
        # Serbian
        "sr": "srp",
        # Swedish
        "sv": "swe",
        # Swahili
        "sw": "swh",
        # Tamil
        "ta": "tam",
        # Telugu
        "te": "tel",
        # Tajik
        "tg": "tgk",
        # Tagalog
        "tl": "tgl",
        # Thai
        "th": "tha",
        # Turkish
        "tr": "tur",
        # Ukrainian
        "uk": "ukr",
        # Urdu
        "ur": "urd",
        # Northern Uzbek
        "uz": "uzn",
        # Vietnamese
        "vi": "vie",
        # Yoruba
        "yo": "yor",
        # Cantonese
        "yue": "yue",
        # Standard Malay
        "ms": "zsm",
        # Zulu
        "zu": "zul",
    }

    @property
    def supported_languages(self):
        return self.language_to_id_mapping.keys()

    def is_supported(self, lang_id: str) -> bool:
        return lang_id in self.supported_languages


class AudioDiarizationInput(BaseModel):
    audio_url: str
    topics: list[TitleSummaryWithId]
