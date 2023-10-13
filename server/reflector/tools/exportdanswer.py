import json
import pathlib
from datetime import timedelta


async def export_db(filename: str) -> None:
    from reflector.settings import settings

    filename = pathlib.Path(filename).resolve()
    settings.DATABASE_URL = f"sqlite:///{filename}"

    from reflector.db import database, transcripts

    await database.connect()
    transcripts = await database.fetch_all(transcripts.select())
    await database.disconnect()

    def export_transcript(transcript, output_dir):
        for topic in transcript.topics:
            metadata = {
                "link": f"https://reflector.media/transcripts/{transcript.id}#topic:{topic['id']},timestamp:{topic['timestamp']}",
                "transcript_id": transcript.id,
                "transcript_created_at": transcript.created_at.isoformat(),
                "topic_id": topic["id"],
                "topic_relative_timestamp": topic["timestamp"],
                "topic_created_at": (
                    transcript.created_at + timedelta(seconds=topic["timestamp"])
                ).isoformat(),
                "topic_title": topic["title"],
            }
            j_metadata = json.dumps(metadata)

            # export transcript
            output = output_dir / f"{transcript.id}-topic-{topic['id']}.txt"
            with open(output, "w", encoding="utf8") as fd:
                fd.write(f"#DANSWER_METADATA={j_metadata}\n")
                fd.write("\n")
                fd.write(f"# {topic['title']}\n")
                fd.write("\n")
                fd.write(f"{topic['transcript']}\n")

            # # export summary
            # output = output_dir / f"{transcript.id}-summary.txt"
            # metadata = {
            #     "link": f"https://reflector.media/transcripts/{transcript.id}",
            #     "rfl_id": transcript.id,
            # }
            #
            # j_metadata = json.dumps(metadata)
            # with open(output, "w", encoding="utf8") as fd:
            #     fd.write(f"#DANSWER_METADATA={j_metadata}\n")
            #     fd.write("\n")
            #     fd.write("# Summary\n")
            #     fd.write("\n")
            #     fd.write(f"{transcript.long_summary}\n")

    output_dir = pathlib.Path("exportdanswer")
    for transcript in transcripts:
        export_transcript(transcript, output_dir)


if __name__ == "__main__":
    import argparse
    import asyncio

    parser = argparse.ArgumentParser()
    parser.add_argument("database", help="Sqlite Database file")
    args = parser.parse_args()

    asyncio.run(export_db(args.database))
