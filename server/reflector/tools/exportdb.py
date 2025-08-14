import csv
import pathlib


async def export_db(filename: str) -> None:
    from reflector.settings import settings

    filename = pathlib.Path(filename).resolve()
    settings.DATABASE_URL = f"sqlite:///{filename}"

    from reflector.db import get_database, transcripts

    database = get_database()
    await database.connect()
    transcripts = await database.fetch_all(transcripts.select())
    await database.disconnect()

    def export_transcript(transcript):
        tid = transcript.id
        yield tid, "title", transcript.title
        yield tid, "name", transcript.name
        yield tid, "created_at", transcript.created_at
        yield tid, "long_summary", transcript.long_summary
        yield tid, "short_summary", transcript.short_summary
        yield tid, "source_language", transcript.source_language
        yield tid, "target_language", transcript.target_language
        yield tid, "user_id", transcript.user_id
        yield tid, "status", transcript.status
        for topic in transcript.topics:
            yield tid, "topic", topic["id"], "title", topic["title"]
            yield tid, "topic", topic["id"], "summary", topic["summary"]
            yield tid, "topic", topic["id"], "timestamp", topic["timestamp"]
            yield tid, "topic", topic["id"], "transcript", topic["transcript"]

        # extract transcripts
        for idx, entry in enumerate(transcript.events):
            if entry["event"] == "TRANSCRIPT":
                yield tid, "event_transcript", idx, "text", entry["data"]["text"]
                if entry["data"].get("translation") is not None:
                    yield (
                        tid,
                        "event_transcript",
                        idx,
                        "translation",
                        entry["data"].get("translation", None),
                    )

    def export_transcripts(transcripts):
        for transcript in transcripts:
            yield from export_transcript(transcript)

    csv_output = pathlib.Path("export.csv").resolve()
    output = csv.writer(open(csv_output, "w"))
    output.writerow(["transcript_id", "key", "value", "key", "value"])
    for row in export_transcripts(transcripts):
        output.writerow(row)

    print(f"Exported {len(transcripts)} transcripts to {csv_output}")


if __name__ == "__main__":
    import argparse
    import asyncio

    parser = argparse.ArgumentParser()
    parser.add_argument("database", help="Sqlite Database file")
    args = parser.parse_args()

    asyncio.run(export_db(args.database))
