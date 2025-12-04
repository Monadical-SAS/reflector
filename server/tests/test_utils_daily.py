import pytest

from reflector.utils.daily import extract_base_room_name, parse_daily_recording_filename


@pytest.mark.parametrize(
    "daily_room_name,expected",
    [
        ("daily-20251020193458", "daily"),
        ("daily-2-20251020193458", "daily-2"),
        ("my-room-name-20251020193458", "my-room-name"),
        ("room-with-numbers-123-20251020193458", "room-with-numbers-123"),
        ("x-20251020193458", "x"),
    ],
)
def test_extract_base_room_name(daily_room_name, expected):
    assert extract_base_room_name(daily_room_name) == expected


@pytest.mark.parametrize(
    "filename,expected_recording_ts,expected_participant_id,expected_track_ts",
    [
        (
            "1763152299562-12f0b87c-97d4-4dd3-a65c-cee1f854a79c-cam-audio-1763152314582",
            1763152299562,
            "12f0b87c-97d4-4dd3-a65c-cee1f854a79c",
            1763152314582,
        ),
        (
            "1760988935484-52f7f48b-fbab-431f-9a50-87b9abfc8255-cam-audio-1760988935922",
            1760988935484,
            "52f7f48b-fbab-431f-9a50-87b9abfc8255",
            1760988935922,
        ),
        (
            "1760988935484-a37c35e3-6f8e-4274-a482-e9d0f102a732-cam-audio-1760988943823",
            1760988935484,
            "a37c35e3-6f8e-4274-a482-e9d0f102a732",
            1760988943823,
        ),
        (
            "path/to/1763151171834-b6719a43-4481-483a-a8fc-2ae18b69283c-cam-audio-1763151180561",
            1763151171834,
            "b6719a43-4481-483a-a8fc-2ae18b69283c",
            1763151180561,
        ),
    ],
)
def test_parse_daily_recording_filename(
    filename, expected_recording_ts, expected_participant_id, expected_track_ts
):
    result = parse_daily_recording_filename(filename)

    assert result.recording_start_ts == expected_recording_ts
    assert result.participant_id == expected_participant_id
    assert result.track_start_ts == expected_track_ts


def test_parse_daily_recording_filename_invalid():
    with pytest.raises(ValueError, match="Invalid Daily.co recording filename"):
        parse_daily_recording_filename("invalid-filename")

    with pytest.raises(ValueError, match="Invalid Daily.co recording filename"):
        parse_daily_recording_filename("123-not-a-uuid-cam-audio-456")
