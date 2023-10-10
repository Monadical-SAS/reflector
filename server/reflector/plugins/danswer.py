import io
import uuid
from datetime import datetime
from json import dumps

from httpx import AsyncClient
from reflector.settings import settings
from reflector.views.transcripts import Transcript, TranscriptTopic


class Danswer:
    def __init__(self):
        self.base_url = settings.DANSWER_URL
        self.client = AsyncClient(base_url=self.base_url)

    def is_enabled(self):
        return self.base_url is not None

    async def upload_chunk(self, transcript: Transcript, chunk: TranscriptTopic):
        ### /api/manage/admin/connector/file/upload
        metadata = {
            "link": f"https://reflector.media/transcripts/{transcript.id}",
            "transcript_id": transcript.id,
            "transcript_created_at": transcript.created_at.isoformat(),
            "chunk_id": chunk.id,
            "chunk_created_at": datetime.utcnow().isoformat(),
            "chunk_relative_timestamp": chunk.timestamp,
        }
        content = "\n".join(
            (
                f"#DANSWER_METADATA={dumps(metadata)}",
                "",
                f"# {chunk.title}",
                "",
                chunk.transcript,
            )
        )

        fd = io.BytesIO(content.encode("utf-8"))
        filename = f"{transcript.id}_{chunk.id}.txt"

        # upload the chunk
        response = await self.client.post(
            "/api/manage/admin/connector/file/upload",
            files={"files": (filename, fd, "text/plain")},
        )
        response.raise_for_status()
        r1 = response.json()

        # update connector
        data = {
            "name": f"FileConnector-{uuid.uuid4().hex}",
            "source": "file",
            "input_type": "load_state",
            "connector_specific_config": {
                "file_locations": r1.get("file_paths"),
            },
            "refresh_freq": None,
            "disabled": False,
        }
        response = await self.client.post(
            "/api/manage/admin/connector",
            json=data,
        )
        response.raise_for_status()
        r2 = response.json()

        # put ?
        data = {"name": filename}
        response = await self.client.put(
            f"api/manage/connector/{r2['id']}/credential/0", json=data
        )
        response.raise_for_status()

        # run once
        data = {
            "connector_id": r2["id"],
            "credentialIds": [0],
        }
        response = await self.client.post(
            "api/manage/admin/connector/run-once", json=data
        )
        response.raise_for_status()

    async def search(self, prompt):
        pass


if __name__ == "__main__":
    danswer = Danswer()

    dbtranscript = Transcript(
        id=uuid.uuid4().hex,
        created_at=datetime.utcnow(),
    )

    chunk = TranscriptTopic(
        id=uuid.uuid4().hex,
        title="Test danswer integration",
        summary="This is a test",
        timestamp=0,
        transcript="ppooll",
    )

    import asyncio

    async def upload():
        ret = await danswer.upload_chunk(dbtranscript, chunk)
        print(ret)

    asyncio.run(upload())
