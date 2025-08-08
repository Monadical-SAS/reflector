#!/usr/bin/env python
"""
Script to populate WebVTT field for all transcripts with topics.
This will overwrite existing WebVTT values.
"""

import asyncio
from reflector.db import database
from reflector.db.transcripts import (
    transcripts,
    TranscriptTopic,
)
from reflector.utils.webvtt import topics_to_webvtt


async def migrate_transcript_table_webvtt_column():
    """Populate WebVTT for all transcripts that have topics."""
    
    # Connect to database
    await database.connect()
    
    try:
        # Get all transcripts with topics
        query = transcripts.select().where(
            transcripts.c["topics"].isnot(None)
        )
        
        results = await database.fetch_all(query)
        
        print(f"Found {len(results)} transcripts with topics")
        
        updated_count = 0
        error_count = 0
        
        for row in results:
            transcript_id = row['id']
            topics_data = row["topics"]
            
            if not topics_data:
                continue
            
            try:
                # Convert dict data to TranscriptTopic objects
                topic_objects = [
                    TranscriptTopic(**topic_dict) 
                    for topic_dict in topics_data
                ]
                
                # Generate WebVTT
                webvtt_content = topics_to_webvtt(topic_objects)
                
                # Update the transcript with WebVTT
                update_query = (
                    transcripts.update()
                    .where(transcripts.c.id == transcript_id)
                    .values(**{"webvtt": webvtt_content})
                )
                
                await database.execute(update_query)
                updated_count += 1
                
                print(f"✓ Updated transcript {transcript_id}")
                
            except Exception as e:
                error_count += 1
                print(f"✗ Error updating transcript {transcript_id}: {e}")
        
        print(f"\nMigration complete!")
        print(f"  Updated: {updated_count}")
        print(f"  Errors: {error_count}")
        
    finally:
        await database.disconnect()


if __name__ == "__main__":
    asyncio.run(migrate_transcript_table_webvtt_column())