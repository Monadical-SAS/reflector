import pytest


@pytest.mark.asyncio
async def test_transcript_participants(client):
    response = await client.post("/transcripts", json={"name": "test"})
    assert response.status_code == 200
    assert response.json()["participants"] == []

    # create a participant
    transcript_id = response.json()["id"]
    response = await client.post(
        f"/transcripts/{transcript_id}/participants", json={"name": "test"}
    )
    assert response.status_code == 200
    assert response.json()["id"] is not None
    assert response.json()["speaker"] is None
    assert response.json()["name"] == "test"

    # create another one with a speaker
    response = await client.post(
        f"/transcripts/{transcript_id}/participants",
        json={"name": "test2", "speaker": 1},
    )
    assert response.status_code == 200
    assert response.json()["id"] is not None
    assert response.json()["speaker"] == 1
    assert response.json()["name"] == "test2"

    # get all participants via transcript
    response = await client.get(f"/transcripts/{transcript_id}")
    assert response.status_code == 200
    assert len(response.json()["participants"]) == 2

    # get participants via participants endpoint
    response = await client.get(f"/transcripts/{transcript_id}/participants")
    assert response.status_code == 200
    assert len(response.json()) == 2


@pytest.mark.asyncio
async def test_transcript_participants_same_speaker(client):
    response = await client.post("/transcripts", json={"name": "test"})
    assert response.status_code == 200
    assert response.json()["participants"] == []
    transcript_id = response.json()["id"]

    # create a participant
    response = await client.post(
        f"/transcripts/{transcript_id}/participants",
        json={"name": "test", "speaker": 1},
    )
    assert response.status_code == 200
    assert response.json()["speaker"] == 1

    # create another one with the same speaker
    response = await client.post(
        f"/transcripts/{transcript_id}/participants",
        json={"name": "test2", "speaker": 1},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_transcript_participants_update_name(client):
    response = await client.post("/transcripts", json={"name": "test"})
    assert response.status_code == 200
    assert response.json()["participants"] == []
    transcript_id = response.json()["id"]

    # create a participant
    response = await client.post(
        f"/transcripts/{transcript_id}/participants",
        json={"name": "test", "speaker": 1},
    )
    assert response.status_code == 200
    assert response.json()["speaker"] == 1

    # update the participant
    participant_id = response.json()["id"]
    response = await client.patch(
        f"/transcripts/{transcript_id}/participants/{participant_id}",
        json={"name": "test2"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "test2"

    # verify the participant was updated
    response = await client.get(
        f"/transcripts/{transcript_id}/participants/{participant_id}"
    )
    assert response.status_code == 200
    assert response.json()["name"] == "test2"

    # verify the participant was updated in transcript
    response = await client.get(f"/transcripts/{transcript_id}")
    assert response.status_code == 200
    assert len(response.json()["participants"]) == 1
    assert response.json()["participants"][0]["name"] == "test2"


@pytest.mark.asyncio
async def test_transcript_participants_update_speaker(client):
    response = await client.post("/transcripts", json={"name": "test"})
    assert response.status_code == 200
    assert response.json()["participants"] == []
    transcript_id = response.json()["id"]

    # create a participant
    response = await client.post(
        f"/transcripts/{transcript_id}/participants",
        json={"name": "test", "speaker": 1},
    )
    assert response.status_code == 200
    participant1_id = response.json()["id"]

    # create another participant
    response = await client.post(
        f"/transcripts/{transcript_id}/participants",
        json={"name": "test2", "speaker": 2},
    )
    assert response.status_code == 200
    participant2_id = response.json()["id"]

    # update the participant, refused as speaker is already taken
    response = await client.patch(
        f"/transcripts/{transcript_id}/participants/{participant2_id}",
        json={"speaker": 1},
    )
    assert response.status_code == 400

    # delete the participant 1
    response = await client.delete(
        f"/transcripts/{transcript_id}/participants/{participant1_id}"
    )
    assert response.status_code == 200

    # update the participant 2 again, should be accepted now
    response = await client.patch(
        f"/transcripts/{transcript_id}/participants/{participant2_id}",
        json={"speaker": 1},
    )
    assert response.status_code == 200

    # ensure participant2 name is still there
    response = await client.get(
        f"/transcripts/{transcript_id}/participants/{participant2_id}"
    )
    assert response.status_code == 200
    assert response.json()["name"] == "test2"
    assert response.json()["speaker"] == 1
