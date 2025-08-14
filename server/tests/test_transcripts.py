from contextlib import asynccontextmanager

import pytest


@pytest.mark.asyncio
async def test_transcript_create(client):
    response = await client.post("/transcripts", json={"name": "test"})
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
async def test_transcript_get_update_name(client):
    response = await client.post("/transcripts", json={"name": "test"})
    assert response.status_code == 200
    assert response.json()["name"] == "test"

    tid = response.json()["id"]

    response = await client.get(f"/transcripts/{tid}")
    assert response.status_code == 200
    assert response.json()["name"] == "test"

    response = await client.patch(f"/transcripts/{tid}", json={"name": "test2"})
    assert response.status_code == 200
    assert response.json()["name"] == "test2"

    response = await client.get(f"/transcripts/{tid}")
    assert response.status_code == 200
    assert response.json()["name"] == "test2"


@pytest.mark.asyncio
async def test_transcript_get_update_locked(client):
    response = await client.post("/transcripts", json={"name": "test"})
    assert response.status_code == 200
    assert response.json()["locked"] is False

    tid = response.json()["id"]

    response = await client.get(f"/transcripts/{tid}")
    assert response.status_code == 200
    assert response.json()["locked"] is False

    response = await client.patch(f"/transcripts/{tid}", json={"locked": True})
    assert response.status_code == 200
    assert response.json()["locked"] is True

    response = await client.get(f"/transcripts/{tid}")
    assert response.status_code == 200
    assert response.json()["locked"] is True


@pytest.mark.asyncio
async def test_transcript_get_update_summary(client):
    response = await client.post("/transcripts", json={"name": "test"})
    assert response.status_code == 200
    assert response.json()["long_summary"] is None
    assert response.json()["short_summary"] is None

    tid = response.json()["id"]

    response = await client.get(f"/transcripts/{tid}")
    assert response.status_code == 200
    assert response.json()["long_summary"] is None
    assert response.json()["short_summary"] is None

    response = await client.patch(
        f"/transcripts/{tid}",
        json={"long_summary": "test_long", "short_summary": "test_short"},
    )
    assert response.status_code == 200
    assert response.json()["long_summary"] == "test_long"
    assert response.json()["short_summary"] == "test_short"

    response = await client.get(f"/transcripts/{tid}")
    assert response.status_code == 200
    assert response.json()["long_summary"] == "test_long"
    assert response.json()["short_summary"] == "test_short"


@pytest.mark.asyncio
async def test_transcript_get_update_title(client):
    response = await client.post("/transcripts", json={"name": "test"})
    assert response.status_code == 200
    assert response.json()["title"] is None

    tid = response.json()["id"]

    response = await client.get(f"/transcripts/{tid}")
    assert response.status_code == 200
    assert response.json()["title"] is None

    response = await client.patch(f"/transcripts/{tid}", json={"title": "test_title"})
    assert response.status_code == 200
    assert response.json()["title"] == "test_title"

    response = await client.get(f"/transcripts/{tid}")
    assert response.status_code == 200
    assert response.json()["title"] == "test_title"


@pytest.mark.asyncio
async def test_transcripts_list_anonymous(client):
    # XXX this test is a bit fragile, as it depends on the storage which
    #     is shared between tests
    from reflector.settings import settings

    response = await client.get("/transcripts")
    assert response.status_code == 401

    # if public mode, it should be allowed
    try:
        settings.PUBLIC_MODE = True
        response = await client.get("/transcripts")
        assert response.status_code == 200
    finally:
        settings.PUBLIC_MODE = False


@asynccontextmanager
async def authenticated_client_ctx():
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


@asynccontextmanager
async def authenticated_client2_ctx():
    from reflector.app import app
    from reflector.auth import current_user, current_user_optional

    app.dependency_overrides[current_user] = lambda: {
        "sub": "randomuserid2",
        "email": "test@mail.com",
    }
    app.dependency_overrides[current_user_optional] = lambda: {
        "sub": "randomuserid2",
        "email": "test@mail.com",
    }
    yield
    del app.dependency_overrides[current_user]
    del app.dependency_overrides[current_user_optional]


@pytest.fixture
@pytest.mark.asyncio
async def authenticated_client():
    async with authenticated_client_ctx():
        yield


@pytest.fixture
@pytest.mark.asyncio
async def authenticated_client2():
    async with authenticated_client2_ctx():
        yield


@pytest.mark.asyncio
async def test_transcripts_list_authenticated(authenticated_client, client):
    # XXX this test is a bit fragile, as it depends on the storage which
    #     is shared between tests

    response = await client.post("/transcripts", json={"name": "testxx1"})
    assert response.status_code == 200
    assert response.json()["name"] == "testxx1"

    response = await client.post("/transcripts", json={"name": "testxx2"})
    assert response.status_code == 200
    assert response.json()["name"] == "testxx2"

    response = await client.get("/transcripts")
    assert response.status_code == 200
    assert len(response.json()["items"]) >= 2
    names = [t["name"] for t in response.json()["items"]]
    assert "testxx1" in names
    assert "testxx2" in names


@pytest.mark.asyncio
async def test_transcript_delete(client):
    response = await client.post("/transcripts", json={"name": "testdel1"})
    assert response.status_code == 200
    assert response.json()["name"] == "testdel1"

    tid = response.json()["id"]
    response = await client.delete(f"/transcripts/{tid}")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

    response = await client.get(f"/transcripts/{tid}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_transcript_mark_reviewed(client):
    response = await client.post("/transcripts", json={"name": "test"})
    assert response.status_code == 200
    assert response.json()["name"] == "test"
    assert response.json()["reviewed"] is False

    tid = response.json()["id"]

    response = await client.get(f"/transcripts/{tid}")
    assert response.status_code == 200
    assert response.json()["name"] == "test"
    assert response.json()["reviewed"] is False

    response = await client.patch(f"/transcripts/{tid}", json={"reviewed": True})
    assert response.status_code == 200
    assert response.json()["reviewed"] is True

    response = await client.get(f"/transcripts/{tid}")
    assert response.status_code == 200
    assert response.json()["reviewed"] is True
