from pydantic import BaseModel
from pathlib import Path


class AudioFile(BaseModel):
    path: Path
    sample_rate: int
    channels: int
    sample_width: int
    timestamp: float = 0.0

    def release(self):
        self.path.unlink()


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
