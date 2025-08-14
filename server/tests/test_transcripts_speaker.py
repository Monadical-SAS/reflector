import pytest


@pytest.mark.asyncio
async def test_transcript_reassign_speaker(fake_transcript_with_topics, client):
    transcript_id = fake_transcript_with_topics.id

    # check the transcript exists
    response = await client.get(f"/transcripts/{transcript_id}")
    assert response.status_code == 200

    # check initial topics of the transcript
    response = await client.get(f"/transcripts/{transcript_id}/topics/with-words")
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
    response = await client.patch(
        f"/transcripts/{transcript_id}/speaker/assign",
        json={
            "speaker": 1,
            "timestamp_from": 0,
            "timestamp_to": 1,
        },
    )
    assert response.status_code == 200

    # check topics again
    response = await client.get(f"/transcripts/{transcript_id}/topics/with-words")
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
    response = await client.patch(
        f"/transcripts/{transcript_id}/speaker/assign",
        json={
            "speaker": 2,
            "timestamp_from": 1,
            "timestamp_to": 2.5,
        },
    )
    assert response.status_code == 200

    # check topics again
    response = await client.get(f"/transcripts/{transcript_id}/topics/with-words")
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
    response = await client.patch(
        f"/transcripts/{transcript_id}/speaker/assign",
        json={
            "speaker": 4,
            "timestamp_from": 0,
            "timestamp_to": 100,
        },
    )
    assert response.status_code == 200

    # check topics again
    response = await client.get(f"/transcripts/{transcript_id}/topics/with-words")
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
async def test_transcript_merge_speaker(fake_transcript_with_topics, client):
    transcript_id = fake_transcript_with_topics.id

    # check the transcript exists
    response = await client.get(f"/transcripts/{transcript_id}")
    assert response.status_code == 200

    # check initial topics of the transcript
    response = await client.get(f"/transcripts/{transcript_id}/topics/with-words")
    assert response.status_code == 200
    topics = response.json()
    assert len(topics) == 2

    # check through words
    assert topics[0]["words"][0]["speaker"] == 0
    assert topics[0]["words"][1]["speaker"] == 0
    assert topics[1]["words"][0]["speaker"] == 0
    assert topics[1]["words"][1]["speaker"] == 0

    # reassign speaker
    response = await client.patch(
        f"/transcripts/{transcript_id}/speaker/assign",
        json={
            "speaker": 1,
            "timestamp_from": 0,
            "timestamp_to": 1,
        },
    )
    assert response.status_code == 200

    # check topics again
    response = await client.get(f"/transcripts/{transcript_id}/topics/with-words")
    assert response.status_code == 200
    topics = response.json()
    assert len(topics) == 2

    # check through words
    assert topics[0]["words"][0]["speaker"] == 1
    assert topics[0]["words"][1]["speaker"] == 1
    assert topics[1]["words"][0]["speaker"] == 0
    assert topics[1]["words"][1]["speaker"] == 0

    # merge speakers
    response = await client.patch(
        f"/transcripts/{transcript_id}/speaker/merge",
        json={
            "speaker_from": 1,
            "speaker_to": 0,
        },
    )
    assert response.status_code == 200

    # check topics again
    response = await client.get(f"/transcripts/{transcript_id}/topics/with-words")
    assert response.status_code == 200
    topics = response.json()
    assert len(topics) == 2

    # check through words
    assert topics[0]["words"][0]["speaker"] == 0
    assert topics[0]["words"][1]["speaker"] == 0
    assert topics[1]["words"][0]["speaker"] == 0
    assert topics[1]["words"][1]["speaker"] == 0


@pytest.mark.asyncio
async def test_transcript_reassign_with_participant(
    fake_transcript_with_topics, client
):
    transcript_id = fake_transcript_with_topics.id

    # check the transcript exists
    response = await client.get(f"/transcripts/{transcript_id}")
    assert response.status_code == 200
    transcript = response.json()
    assert len(transcript["participants"]) == 0

    # create 2 participants
    response = await client.post(
        f"/transcripts/{transcript_id}/participants",
        json={
            "name": "Participant 1",
        },
    )
    assert response.status_code == 200
    participant1_id = response.json()["id"]

    response = await client.post(
        f"/transcripts/{transcript_id}/participants",
        json={
            "name": "Participant 2",
        },
    )
    assert response.status_code == 200
    participant2_id = response.json()["id"]

    # check participants speakers
    response = await client.get(f"/transcripts/{transcript_id}/participants")
    assert response.status_code == 200
    participants = response.json()
    assert len(participants) == 2
    assert participants[0]["name"] == "Participant 1"
    assert participants[0]["speaker"] is None
    assert participants[1]["name"] == "Participant 2"
    assert participants[1]["speaker"] is None

    # check initial topics of the transcript
    response = await client.get(f"/transcripts/{transcript_id}/topics/with-words")
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

    # reassign speaker from a participant
    response = await client.patch(
        f"/transcripts/{transcript_id}/speaker/assign",
        json={
            "participant": participant1_id,
            "timestamp_from": 0,
            "timestamp_to": 1,
        },
    )
    assert response.status_code == 200

    # check participants if speaker has been assigned
    # first participant should have 1, because it's not used yet.
    response = await client.get(f"/transcripts/{transcript_id}/participants")
    assert response.status_code == 200
    participants = response.json()
    assert len(participants) == 2
    assert participants[0]["name"] == "Participant 1"
    assert participants[0]["speaker"] == 1
    assert participants[1]["name"] == "Participant 2"
    assert participants[1]["speaker"] is None

    # check topics again
    response = await client.get(f"/transcripts/{transcript_id}/topics/with-words")
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

    # reassign participant, middle of 2 topics
    response = await client.patch(
        f"/transcripts/{transcript_id}/speaker/assign",
        json={
            "participant": participant2_id,
            "timestamp_from": 1,
            "timestamp_to": 2.5,
        },
    )
    assert response.status_code == 200

    # check participants if speaker has been assigned
    # first participant should have 1, because it's not used yet.
    response = await client.get(f"/transcripts/{transcript_id}/participants")
    assert response.status_code == 200
    participants = response.json()
    assert len(participants) == 2
    assert participants[0]["name"] == "Participant 1"
    assert participants[0]["speaker"] == 1
    assert participants[1]["name"] == "Participant 2"
    assert participants[1]["speaker"] == 2

    # check topics again
    response = await client.get(f"/transcripts/{transcript_id}/topics/with-words")
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
    response = await client.patch(
        f"/transcripts/{transcript_id}/speaker/assign",
        json={
            "participant": participant1_id,
            "timestamp_from": 0,
            "timestamp_to": 100,
        },
    )
    assert response.status_code == 200

    # check topics again
    response = await client.get(f"/transcripts/{transcript_id}/topics/with-words")
    assert response.status_code == 200
    topics = response.json()
    assert len(topics) == 2

    # check through words
    assert topics[0]["words"][0]["speaker"] == 1
    assert topics[0]["words"][1]["speaker"] == 1
    assert topics[1]["words"][0]["speaker"] == 1
    assert topics[1]["words"][1]["speaker"] == 1
    # check segments
    assert len(topics[0]["segments"]) == 1
    assert topics[0]["segments"][0]["speaker"] == 1
    assert len(topics[1]["segments"]) == 1
    assert topics[1]["segments"][0]["speaker"] == 1


@pytest.mark.asyncio
async def test_transcript_reassign_edge_cases(fake_transcript_with_topics, client):
    transcript_id = fake_transcript_with_topics.id

    # check the transcript exists
    response = await client.get(f"/transcripts/{transcript_id}")
    assert response.status_code == 200
    transcript = response.json()
    assert len(transcript["participants"]) == 0

    # try reassign without any participant_id or speaker
    response = await client.patch(
        f"/transcripts/{transcript_id}/speaker/assign",
        json={
            "timestamp_from": 0,
            "timestamp_to": 1,
        },
    )
    assert response.status_code == 400

    # try reassing with both participant_id and speaker
    response = await client.patch(
        f"/transcripts/{transcript_id}/speaker/assign",
        json={
            "participant": "123",
            "speaker": 1,
            "timestamp_from": 0,
            "timestamp_to": 1,
        },
    )
    assert response.status_code == 400

    # try reassing with non-existing participant_id
    response = await client.patch(
        f"/transcripts/{transcript_id}/speaker/assign",
        json={
            "participant": "123",
            "timestamp_from": 0,
            "timestamp_to": 1,
        },
    )
    assert response.status_code == 404
