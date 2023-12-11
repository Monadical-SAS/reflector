import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_transcript_reassign_speaker(fake_transcript_with_topics):
    from reflector.app import app

    transcript_id = fake_transcript_with_topics.id

    async with AsyncClient(app=app, base_url="http://test/v1") as ac:
        # check the transcript exists
        response = await ac.get(f"/transcripts/{transcript_id}")
        assert response.status_code == 200

        # check initial topics of the transcript
        response = await ac.get(f"/transcripts/{transcript_id}/topics/with-words")
        assert response.status_code == 200
        topics = response.json()
        assert len(topics) == 2

        # check through words
        assert topics[0]["words"][0]["speaker"] == 0
        assert topics[0]["words"][1]["speaker"] == 0
        assert topics[1]["words"][0]["speaker"] == 0
        assert topics[1]["words"][1]["speaker"] == 0
        # check through segments
        assert len(topics[0]["segments"]) == 1
        assert topics[0]["segments"][0]["speaker"] == 0
        assert len(topics[1]["segments"]) == 1
        assert topics[1]["segments"][0]["speaker"] == 0

        # reassign speaker
        response = await ac.patch(
            f"/transcripts/{transcript_id}/speaker/assign",
            json={
                "speaker": 1,
                "timestamp_from": 0,
                "timestamp_to": 1,
            },
        )
        assert response.status_code == 200

        # check topics again
        response = await ac.get(f"/transcripts/{transcript_id}/topics/with-words")
        assert response.status_code == 200
        topics = response.json()
        assert len(topics) == 2

        # check through words
        assert topics[0]["words"][0]["speaker"] == 1
        assert topics[0]["words"][1]["speaker"] == 1
        assert topics[1]["words"][0]["speaker"] == 0
        assert topics[1]["words"][1]["speaker"] == 0
        # check segments
        assert len(topics[0]["segments"]) == 1
        assert topics[0]["segments"][0]["speaker"] == 1
        assert len(topics[1]["segments"]) == 1
        assert topics[1]["segments"][0]["speaker"] == 0

        # reassign speaker, middle of 2 topics
        response = await ac.patch(
            f"/transcripts/{transcript_id}/speaker/assign",
            json={
                "speaker": 2,
                "timestamp_from": 1,
                "timestamp_to": 2.5,
            },
        )
        assert response.status_code == 200

        # check topics again
        response = await ac.get(f"/transcripts/{transcript_id}/topics/with-words")
        assert response.status_code == 200
        topics = response.json()
        assert len(topics) == 2

        # check through words
        assert topics[0]["words"][0]["speaker"] == 1
        assert topics[0]["words"][1]["speaker"] == 2
        assert topics[1]["words"][0]["speaker"] == 2
        assert topics[1]["words"][1]["speaker"] == 0
        # check segments
        assert len(topics[0]["segments"]) == 2
        assert topics[0]["segments"][0]["speaker"] == 1
        assert topics[0]["segments"][1]["speaker"] == 2
        assert len(topics[1]["segments"]) == 2
        assert topics[1]["segments"][0]["speaker"] == 2
        assert topics[1]["segments"][1]["speaker"] == 0

        # reassign speaker, everything
        response = await ac.patch(
            f"/transcripts/{transcript_id}/speaker/assign",
            json={
                "speaker": 4,
                "timestamp_from": 0,
                "timestamp_to": 100,
            },
        )
        assert response.status_code == 200

        # check topics again
        response = await ac.get(f"/transcripts/{transcript_id}/topics/with-words")
        assert response.status_code == 200
        topics = response.json()
        assert len(topics) == 2

        # check through words
        assert topics[0]["words"][0]["speaker"] == 4
        assert topics[0]["words"][1]["speaker"] == 4
        assert topics[1]["words"][0]["speaker"] == 4
        assert topics[1]["words"][1]["speaker"] == 4
        # check segments
        assert len(topics[0]["segments"]) == 1
        assert topics[0]["segments"][0]["speaker"] == 4
        assert len(topics[1]["segments"]) == 1
        assert topics[1]["segments"][0]["speaker"] == 4


@pytest.mark.asyncio
async def test_transcript_merge_speaker(fake_transcript_with_topics):
    from reflector.app import app

    transcript_id = fake_transcript_with_topics.id

    async with AsyncClient(app=app, base_url="http://test/v1") as ac:
        # check the transcript exists
        response = await ac.get(f"/transcripts/{transcript_id}")
        assert response.status_code == 200

        # check initial topics of the transcript
        response = await ac.get(f"/transcripts/{transcript_id}/topics/with-words")
        assert response.status_code == 200
        topics = response.json()
        assert len(topics) == 2

        # check through words
        assert topics[0]["words"][0]["speaker"] == 0
        assert topics[0]["words"][1]["speaker"] == 0
        assert topics[1]["words"][0]["speaker"] == 0
        assert topics[1]["words"][1]["speaker"] == 0

        # reassign speaker
        response = await ac.patch(
            f"/transcripts/{transcript_id}/speaker/assign",
            json={
                "speaker": 1,
                "timestamp_from": 0,
                "timestamp_to": 1,
            },
        )
        assert response.status_code == 200

        # check topics again
        response = await ac.get(f"/transcripts/{transcript_id}/topics/with-words")
        assert response.status_code == 200
        topics = response.json()
        assert len(topics) == 2

        # check through words
        assert topics[0]["words"][0]["speaker"] == 1
        assert topics[0]["words"][1]["speaker"] == 1
        assert topics[1]["words"][0]["speaker"] == 0
        assert topics[1]["words"][1]["speaker"] == 0

        # merge speakers
        response = await ac.patch(
            f"/transcripts/{transcript_id}/speaker/merge",
            json={
                "speaker_from": 1,
                "speaker_to": 0,
            },
        )
        assert response.status_code == 200

        # check topics again
        response = await ac.get(f"/transcripts/{transcript_id}/topics/with-words")
        assert response.status_code == 200
        topics = response.json()
        assert len(topics) == 2

        # check through words
        assert topics[0]["words"][0]["speaker"] == 0
        assert topics[0]["words"][1]["speaker"] == 0
        assert topics[1]["words"][0]["speaker"] == 0
        assert topics[1]["words"][1]["speaker"] == 0
