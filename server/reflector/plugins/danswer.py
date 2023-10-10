import asyncio
import io
import uuid
from datetime import datetime
from json import dumps, loads

from httpx import AsyncClient
from reflector.logger import logger
from reflector.plugins.manager import Plugin, PluginManager
from reflector.settings import settings
from reflector.views.transcripts import Transcript, TranscriptTopic


class Danswer(Plugin):
    def __init__(self):
        self.base_url = settings.PLUGIN_DANSWER_URL
        self.client = AsyncClient(base_url=self.base_url, timeout=120)
        self.background_task = set()

    async def load(self):
        pass

    async def unload(self):
        logger.info("Flushing background tasks")
        await asyncio.gather(*self.background_task)

    async def hook(self, name, **kwargs):
        if name == PluginManager.Hook.TRANSCRIPT_TOPIC:
            task = asyncio.create_task(self.upload_topic(**kwargs))
            self.background_task.add(task)
            task.add_done_callback(self.background_task.discard)

    async def upload_topic(self, transcript: Transcript, topic: TranscriptTopic):
        try:
            return await self._upload_topic(transcript, topic)
        except Exception:
            logger.exception("Error uploading topic")
            return None

    async def _upload_topic(self, transcript: Transcript, topic: TranscriptTopic):
        ### /api/manage/admin/connector/file/upload
        metadata = {
            "link": (
                f"https://reflector.media/transcripts/{transcript.id}"
                f"#topic:{topic.id},timestamp:{topic.timestamp}"
            ),
            "transcript_id": transcript.id,
            "transcript_created_at": transcript.created_at.isoformat(),
            "topic_id": topic.id,
            "topic_created_at": datetime.utcnow().isoformat(),
            "topic_relative_timestamp": topic.timestamp,
        }
        content = "\n".join(
            (
                f"#DANSWER_METADATA={dumps(metadata)}",
                "",
                f"# {topic.title}",
                "",
                topic.transcript,
            )
        )

        fd = io.BytesIO(content.encode("utf-8"))
        filename = f"{transcript.id}_{topic.id}.txt"

        # upload the topic
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
        # unfinished
        data = {
            "query": prompt,
            "collection": "danswer_index",
            "use_keyword": False,
            "offset": 0,
        }
        response = await self.client.post("api/stream-direct-qa", json=data)
        response.raise_for_status()
        content = response.content
        content = content.decode("utf-8").split("\n")

        result = {"answer": "", "top_documents": [], "others": []}

        for line in content:
            try:
                j_line = loads(line)
                if "answer_piece" in j_line:
                    result["answer"] += j_line["answer_piece"]
                elif "top_documents" in j_line:
                    for document in j_line["top_documents"]:
                        result["top_documents"].append(loads(document))
                else:
                    result["others"].append(j_line)
            except Exception:
                logger.warning(f"Error parsing danswer response: {line!r}")
        return result


if __name__ == "__main__":
    import argparse

    danswer = Danswer()

    parser = argparse.ArgumentParser()
    parser.add_argument("--search", type=str)
    parser.add_argument("--upload", type=str)
    args = parser.parse_args()

    if args.search:

        async def main():
            ret = await danswer.search(args.search)
            print(ret)

    elif args.upload:
        transcript = Transcript(
            id=uuid.uuid4().hex,
            created_at=datetime.utcnow(),
        )

        topic = TranscriptTopic(
            id=uuid.uuid4().hex,
            title="Test danswer integration",
            summary="This is a test",
            timestamp=0,
            transcript="ppooll",
        )

        async def main():
            result = await danswer.upload_topic(transcript, topic)
            from pprint import pprint

            pprint(result)

    asyncio.run(main())

PluginManager.register("danswer", Danswer)
