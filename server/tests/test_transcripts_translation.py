import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_transcript_create_default_translation():
    from reflector.app import app

    async with AsyncClient(app=app, base_url="http://test/v1") as ac:
        response = await ac.post("/transcripts", json={"name": "test en"})
        assert response.status_code == 200
        assert response.json()["name"] == "test en"
        assert response.json()["source_language"] == "eng"
        assert response.json()["target_language"] == "eng"
        tid = response.json()["id"]

        response = await ac.get(f"/transcripts/{tid}")
        assert response.status_code == 200
        assert response.json()["name"] == "test en"
        assert response.json()["source_language"] == "eng"
        assert response.json()["target_language"] == "eng"


@pytest.mark.asyncio
async def test_transcript_create_en_fr_translation():
    from reflector.app import app

    async with AsyncClient(app=app, base_url="http://test/v1") as ac:
        response = await ac.post(
            "/transcripts", json={"name": "test en/fr", "target_language": "fr"}
        )
        assert response.status_code == 200
        assert response.json()["name"] == "test en/fr"
        assert response.json()["source_language"] == "eng"
        assert response.json()["target_language"] == "fra"
        tid = response.json()["id"]

        response = await ac.get(f"/transcripts/{tid}")
        assert response.status_code == 200
        assert response.json()["name"] == "test en/fr"
        assert response.json()["source_language"] == "eng"
        assert response.json()["target_language"] == "fra"


@pytest.mark.asyncio
async def test_transcript_create_fr_en_translation():
    from reflector.app import app

    async with AsyncClient(app=app, base_url="http://test/v1") as ac:
        response = await ac.post(
            "/transcripts", json={"name": "test fr/en", "source_language": "fr"}
        )
        assert response.status_code == 200
        assert response.json()["name"] == "test fr/en"
        assert response.json()["source_language"] == "fra"
        assert response.json()["target_language"] == "eng"
        tid = response.json()["id"]

        response = await ac.get(f"/transcripts/{tid}")
        assert response.status_code == 200
        assert response.json()["name"] == "test fr/en"
        assert response.json()["source_language"] == "fra"
        assert response.json()["target_language"] == "eng"
