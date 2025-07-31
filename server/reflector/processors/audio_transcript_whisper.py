from faster_whisper import WhisperModel
from reflector.processors.audio_transcript import AudioTranscriptProcessor
from reflector.processors.audio_transcript_auto import AudioTranscriptAutoProcessor
from reflector.processors.types import AudioFile, Transcript, Word


class AudioTranscriptWhisperProcessor(AudioTranscriptProcessor):
    def __init__(self):
        super().__init__()
        self.model = WhisperModel(
            "tiny", device="cpu", compute_type="float32", num_workers=12
        )

    async def _transcript(self, data: AudioFile):
        segments, _ = self.model.transcribe(
            data.path.as_posix(),
            language="en",
            beam_size=5,
            # condition_on_previous_text=True,
            word_timestamps=True,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500},
        )

        if not segments:
            return

        transcript = Transcript(words=[])
        segments = list(segments)
        ts = data.timestamp

        for segment in segments:
            for word in segment.words:
                transcript.words.append(
                    Word(
                        text=word.word,
                        start=round(ts + word.start, 3),
                        end=round(ts + word.end, 3),
                    )
                )

        return transcript


AudioTranscriptAutoProcessor.register("whisper", AudioTranscriptWhisperProcessor)
