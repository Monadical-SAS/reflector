from reflector.processors.base import Processor
from reflector.processors.types import AudioDiarizationInput, TitleSummary


class AudioDiarizationProcessor(Processor):
    INPUT_TYPE = AudioDiarizationInput
    OUTPUT_TYPE = TitleSummary

    async def _push(self, data: AudioDiarizationInput):
        # Gather diarization data
        diarization = [
            {"start": 0.0, "stop": 4.9, "speaker": 2},
            {"start": 5.6, "stop": 6.7, "speaker": 2},
            {"start": 7.3, "stop": 8.9, "speaker": 2},
            {"start": 7.3, "stop": 7.9, "speaker": 0},
            {"start": 9.4, "stop": 11.2, "speaker": 2},
            {"start": 9.7, "stop": 10.0, "speaker": 0},
            {"start": 10.0, "stop": 10.1, "speaker": 0},
            {"start": 11.7, "stop": 16.1, "speaker": 2},
            {"start": 11.8, "stop": 12.1, "speaker": 1},
            {"start": 16.4, "stop": 21.0, "speaker": 2},
            {"start": 21.1, "stop": 22.6, "speaker": 2},
            {"start": 24.7, "stop": 31.9, "speaker": 2},
            {"start": 32.0, "stop": 32.8, "speaker": 1},
            {"start": 33.4, "stop": 37.8, "speaker": 2},
            {"start": 37.9, "stop": 40.3, "speaker": 0},
            {"start": 39.2, "stop": 40.4, "speaker": 2},
            {"start": 40.7, "stop": 41.4, "speaker": 0},
            {"start": 41.6, "stop": 45.7, "speaker": 2},
            {"start": 46.4, "stop": 53.1, "speaker": 2},
            {"start": 53.6, "stop": 56.5, "speaker": 2},
            {"start": 54.9, "stop": 75.4, "speaker": 1},
            {"start": 57.3, "stop": 58.0, "speaker": 2},
            {"start": 65.7, "stop": 66.0, "speaker": 2},
            {"start": 75.8, "stop": 78.8, "speaker": 1},
            {"start": 79.0, "stop": 82.6, "speaker": 1},
            {"start": 83.2, "stop": 83.3, "speaker": 1},
            {"start": 84.5, "stop": 94.3, "speaker": 1},
            {"start": 95.1, "stop": 100.7, "speaker": 1},
            {"start": 100.7, "stop": 102.0, "speaker": 0},
            {"start": 100.7, "stop": 101.8, "speaker": 1},
            {"start": 102.0, "stop": 103.0, "speaker": 1},
            {"start": 103.0, "stop": 103.7, "speaker": 0},
            {"start": 103.7, "stop": 103.8, "speaker": 1},
            {"start": 103.8, "stop": 113.9, "speaker": 0},
            {"start": 114.7, "stop": 117.0, "speaker": 0},
            {"start": 117.0, "stop": 117.4, "speaker": 1},
        ]

        # now reapply speaker to topics (if any)
        # topics is a list[BaseModel] with an attribute words
        # words is a list[BaseModel] with text, start and speaker attribute

        print("IN DIARIZATION PROCESSOR", data)

        # mutate in place
        for topic in data.topics:
            for word in topic.transcript.words:
                for d in diarization:
                    if d["start"] <= word.start <= d["stop"]:
                        word.speaker = d["speaker"]

        # emit them
        for topic in data.topics:
            await self.emit(topic)
