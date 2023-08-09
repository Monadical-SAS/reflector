import pytest
from httpx import AsyncClient
from reflector.app import app


@pytest.mark.asyncio
async def test_transcript_create():
    async with AsyncClient(app=app, base_url="http://test/v1") as ac:
        response = await ac.post("/transcripts", json={"name": "test"})
        assert response.status_code == 200
        assert response.json()["name"] == "test"
        assert response.json()["status"] == "idle"
        assert response.json()["locked"] is False
        assert response.json()["id"] is not None
        assert response.json()["created_at"] is not None

        # ensure some fields are not returned
        assert "topics" not in response.json()
        assert "events" not in response.json()


@pytest.mark.asyncio
async def test_transcript_get_update_name():
    async with AsyncClient(app=app, base_url="http://test/v1") as ac:
        response = await ac.post("/transcripts", json={"name": "test"})
        assert response.status_code == 200
        assert response.json()["name"] == "test"

        tid = response.json()["id"]

        response = await ac.get(f"/transcripts/{tid}")
        assert response.status_code == 200
        assert response.json()["name"] == "test"

        response = await ac.patch(f"/transcripts/{tid}", json={"name": "test2"})
        assert response.status_code == 200
        assert response.json()["name"] == "test2"

        response = await ac.get(f"/transcripts/{tid}")
        assert response.status_code == 200
        assert response.json()["name"] == "test2"


@pytest.mark.asyncio
async def test_transcripts_list():
    # XXX this test is a bit fragile, as it depends on the storage which
    #     is shared between tests
    async with AsyncClient(app=app, base_url="http://test/v1") as ac:
        response = await ac.post("/transcripts", json={"name": "testxx1"})
        assert response.status_code == 200
        assert response.json()["name"] == "testxx1"

        response = await ac.post("/transcripts", json={"name": "testxx2"})
        assert response.status_code == 200
        assert response.json()["name"] == "testxx2"

        response = await ac.get("/transcripts")
        assert response.status_code == 200
        assert len(response.json()["items"]) >= 2
        names = [t["name"] for t in response.json()["items"]]
        assert "testxx1" in names
        assert "testxx2" in names


@pytest.mark.asyncio
async def test_transcript_delete():
    async with AsyncClient(app=app, base_url="http://test/v1") as ac:
        response = await ac.post("/transcripts", json={"name": "testdel1"})
        assert response.status_code == 200
        assert response.json()["name"] == "testdel1"

        tid = response.json()["id"]
        response = await ac.delete(f"/transcripts/{tid}")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

        response = await ac.get(f"/transcripts/{tid}")
        assert response.status_code == 404
