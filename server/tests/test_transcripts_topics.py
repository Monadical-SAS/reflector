import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_transcript_topics(fake_transcript_with_topics):
    from reflector.app import app

    transcript_id = fake_transcript_with_topics.id

    async with AsyncClient(app=app, base_url="http://test/v1") as ac:
        # check the transcript exists
        response = await ac.get(f"/transcripts/{transcript_id}/topics")
        assert response.status_code == 200
        assert len(response.json()) == 2
        topic_id = response.json()[0]["id"]

        # get words per speakers
        response = await ac.get(
            f"/transcripts/{transcript_id}/topics/{topic_id}/words-per-speaker"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["words_per_speaker"]) == 1
        assert data["words_per_speaker"][0]["speaker"] == 0
        assert len(data["words_per_speaker"][0]["words"]) == 2
