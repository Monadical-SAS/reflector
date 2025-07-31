from unittest import mock

import pytest


@pytest.mark.parametrize(
    "name,diarization,expected",
    [
        [
            "no overlap",
            [
                {"start": 0.0, "end": 1.0, "speaker": "A"},
                {"start": 1.0, "end": 2.0, "speaker": "B"},
            ],
            ["A", "A", "B", "B"],
        ],
        [
            "same speaker",
            [
                {"start": 0.0, "end": 1.0, "speaker": "A"},
                {"start": 1.0, "end": 2.0, "speaker": "A"},
            ],
            ["A", "A", "A", "A"],
        ],
        [
            # first segment is removed because it overlap
            # with the second segment, and it is smaller
            "overlap at 0.5s",
            [
                {"start": 0.0, "end": 1.0, "speaker": "A"},
                {"start": 0.5, "end": 2.0, "speaker": "B"},
            ],
            ["B", "B", "B", "B"],
        ],
        [
            "junk segment at 0.5s for 0.2s",
            [
                {"start": 0.0, "end": 1.0, "speaker": "A"},
                {"start": 0.5, "end": 0.7, "speaker": "B"},
                {"start": 1, "end": 2.0, "speaker": "B"},
            ],
            ["A", "A", "B", "B"],
        ],
        [
            "start without diarization",
            [
                {"start": 0.5, "end": 1.0, "speaker": "A"},
                {"start": 1.0, "end": 2.0, "speaker": "B"},
            ],
            ["A", "A", "B", "B"],
        ],
        [
            "end missing diarization",
            [
                {"start": 0.0, "end": 1.0, "speaker": "A"},
                {"start": 1.0, "end": 1.5, "speaker": "B"},
            ],
            ["A", "A", "B", "B"],
        ],
        [
            "continuation of next speaker",
            [
                {"start": 0.0, "end": 0.9, "speaker": "A"},
                {"start": 1.5, "end": 2.0, "speaker": "B"},
            ],
            ["A", "A", "B", "B"],
        ],
        [
            "continuation of previous speaker",
            [
                {"start": 0.0, "end": 0.5, "speaker": "A"},
                {"start": 1.0, "end": 2.0, "speaker": "B"},
            ],
            ["A", "A", "B", "B"],
        ],
        [
            "segment without words",
            [
                {"start": 0.0, "end": 1.0, "speaker": "A"},
                {"start": 1.0, "end": 2.0, "speaker": "B"},
                {"start": 2.0, "end": 3.0, "speaker": "X"},
            ],
            ["A", "A", "B", "B"],
        ],
    ],
)
@pytest.mark.asyncio
async def test_processors_audio_diarization(name, diarization, expected):
    from reflector.processors.audio_diarization import AudioDiarizationProcessor
    from reflector.processors.types import (
        AudioDiarizationInput,
        TitleSummaryWithId,
        Transcript,
        Word,
    )

    # create fake topic
    topics = [
        TitleSummaryWithId(
            id="1",
            title="Title1",
            summary="Summary1",
            timestamp=0.0,
            duration=1.0,
            transcript=Transcript(
                words=[
                    Word(text="Word1", start=0.0, end=0.5),
                    Word(text="word2.", start=0.5, end=1.0),
                ]
            ),
        ),
        TitleSummaryWithId(
            id="2",
            title="Title2",
            summary="Summary2",
            timestamp=0.0,
            duration=1.0,
            transcript=Transcript(
                words=[
                    Word(text="Word3", start=1.0, end=1.5),
                    Word(text="word4.", start=1.5, end=2.0),
                ]
            ),
        ),
    ]

    diarizer = AudioDiarizationProcessor()
    with mock.patch.object(diarizer, "_diarize") as mock_diarize:
        mock_diarize.return_value = diarization

        data = AudioDiarizationInput(
            audio_url="https://example.com/audio.mp3",
            topics=topics,
        )
        await diarizer._push(data)

        # check that the speaker has been assigned to the words
        assert topics[0].transcript.words[0].speaker == expected[0]
        assert topics[0].transcript.words[1].speaker == expected[1]
        assert topics[1].transcript.words[0].speaker == expected[2]
        assert topics[1].transcript.words[1].speaker == expected[3]
