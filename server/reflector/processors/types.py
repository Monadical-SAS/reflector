from pydantic import BaseModel, PrivateAttr
from pathlib import Path
import tempfile
import io


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
        return Transcript(text=self.text, words=words)


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
