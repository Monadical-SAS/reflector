import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_transcript_create():
    from reflector.app import app

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
    from reflector.app import app

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
async def test_transcript_get_update_locked():
    from reflector.app import app

    async with AsyncClient(app=app, base_url="http://test/v1") as ac:
        response = await ac.post("/transcripts", json={"name": "test"})
        assert response.status_code == 200
        assert response.json()["locked"] is False

        tid = response.json()["id"]

        response = await ac.get(f"/transcripts/{tid}")
        assert response.status_code == 200
        assert response.json()["locked"] is False

        response = await ac.patch(f"/transcripts/{tid}", json={"locked": True})
        assert response.status_code == 200
        assert response.json()["locked"] is True

        response = await ac.get(f"/transcripts/{tid}")
        assert response.status_code == 200
        assert response.json()["locked"] is True


@pytest.mark.asyncio
async def test_transcript_get_update_summary():
    from reflector.app import app

    async with AsyncClient(app=app, base_url="http://test/v1") as ac:
        response = await ac.post("/transcripts", json={"name": "test"})
        assert response.status_code == 200
        assert response.json()["long_summary"] is None
        assert response.json()["short_summary"] is None

        tid = response.json()["id"]

        response = await ac.get(f"/transcripts/{tid}")
        assert response.status_code == 200
        assert response.json()["long_summary"] is None
        assert response.json()["short_summary"] is None

        response = await ac.patch(
            f"/transcripts/{tid}",
            json={"long_summary": "test_long", "short_summary": "test_short"},
        )
        assert response.status_code == 200
        assert response.json()["long_summary"] == "test_long"
        assert response.json()["short_summary"] == "test_short"

        response = await ac.get(f"/transcripts/{tid}")
        assert response.status_code == 200
        assert response.json()["long_summary"] == "test_long"
        assert response.json()["short_summary"] == "test_short"


@pytest.mark.asyncio
async def test_transcript_get_update_title():
    from reflector.app import app

    async with AsyncClient(app=app, base_url="http://test/v1") as ac:
        response = await ac.post("/transcripts", json={"name": "test"})
        assert response.status_code == 200
        assert response.json()["title"] is None

        tid = response.json()["id"]

        response = await ac.get(f"/transcripts/{tid}")
        assert response.status_code == 200
        assert response.json()["title"] is None

        response = await ac.patch(f"/transcripts/{tid}", json={"title": "test_title"})
        assert response.status_code == 200
        assert response.json()["title"] == "test_title"

        response = await ac.get(f"/transcripts/{tid}")
        assert response.status_code == 200
        assert response.json()["title"] == "test_title"


@pytest.mark.asyncio
async def test_transcripts_list_anonymous():
    # XXX this test is a bit fragile, as it depends on the storage which
    #     is shared between tests
    from reflector.app import app
    from reflector.settings import settings

    async with AsyncClient(app=app, base_url="http://test/v1") as ac:
        response = await ac.get("/transcripts")
        assert response.status_code == 401

    # if public mode, it should be allowed
    try:
        settings.PUBLIC_MODE = True
        async with AsyncClient(app=app, base_url="http://test/v1") as ac:
            response = await ac.get("/transcripts")
            assert response.status_code == 200
    finally:
        settings.PUBLIC_MODE = False


@pytest.fixture
@pytest.mark.asyncio
async def authenticated_client():
    from reflector.app import app
    from reflector.auth import current_user, current_user_optional

    app.dependency_overrides[current_user] = lambda: {
        "sub": "randomuserid",
        "email": "test@mail.com",
    }
    app.dependency_overrides[current_user_optional] = lambda: {
        "sub": "randomuserid",
        "email": "test@mail.com",
    }
    yield
    del app.dependency_overrides[current_user]
    del app.dependency_overrides[current_user_optional]


@pytest.mark.asyncio
async def test_transcripts_list_authenticated(authenticated_client):
    # XXX this test is a bit fragile, as it depends on the storage which
    #     is shared between tests
    from reflector.app import app

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
    from reflector.app import app

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


@pytest.mark.asyncio
async def test_transcript_mark_reviewed():
    from reflector.app import app

    async with AsyncClient(app=app, base_url="http://test/v1") as ac:
        response = await ac.post("/transcripts", json={"name": "test"})
        assert response.status_code == 200
        assert response.json()["name"] == "test"
        assert response.json()["reviewed"] is False

        tid = response.json()["id"]

        response = await ac.get(f"/transcripts/{tid}")
        assert response.status_code == 200
        assert response.json()["name"] == "test"
        assert response.json()["reviewed"] is False

        response = await ac.patch(f"/transcripts/{tid}", json={"reviewed": True})
        assert response.status_code == 200
        assert response.json()["reviewed"] is True

        response = await ac.get(f"/transcripts/{tid}")
        assert response.status_code == 200
        assert response.json()["reviewed"] is True
