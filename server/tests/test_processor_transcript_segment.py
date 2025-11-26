def test_processor_transcript_segment():
    from reflector.processors.types import Transcript, Word

    transcript = Transcript(
        words=[
            Word(text=" the", start=5.12, end=5.48, speaker=0),
            Word(text=" different", start=5.48, end=5.8, speaker=0),
            Word(text=" projects", start=5.8, end=6.3, speaker=0),
            Word(text=" that", start=6.3, end=6.5, speaker=0),
            Word(text=" are", start=6.5, end=6.58, speaker=0),
            Word(text=" going", start=6.58, end=6.82, speaker=0),
            Word(text=" on", start=6.82, end=7.26, speaker=0),
            Word(text=" to", start=7.26, end=7.4, speaker=0),
            Word(text=" give", start=7.4, end=7.54, speaker=0),
            Word(text=" you", start=7.54, end=7.9, speaker=0),
            Word(text=" context", start=7.9, end=8.24, speaker=0),
            Word(text=" and", start=8.24, end=8.66, speaker=0),
            Word(text=" I", start=8.66, end=8.72, speaker=0),
            Word(text=" think", start=8.72, end=8.82, speaker=0),
            Word(text=" that's", start=8.82, end=9.04, speaker=0),
            Word(text=" what", start=9.04, end=9.12, speaker=0),
            Word(text=" we'll", start=9.12, end=9.24, speaker=0),
            Word(text=" do", start=9.24, end=9.32, speaker=0),
            Word(text=" this", start=9.32, end=9.52, speaker=0),
            Word(text=" week.", start=9.52, end=9.76, speaker=0),
            Word(text=" Um,", start=10.24, end=10.62, speaker=0),
            Word(text=" so,", start=11.36, end=11.94, speaker=0),
            Word(text=" um,", start=12.46, end=12.92, speaker=0),
            Word(text=" what", start=13.74, end=13.94, speaker=0),
            Word(text=" we're", start=13.94, end=14.1, speaker=0),
            Word(text=" going", start=14.1, end=14.24, speaker=0),
            Word(text=" to", start=14.24, end=14.34, speaker=0),
            Word(text=" do", start=14.34, end=14.8, speaker=0),
            Word(text=" at", start=14.8, end=14.98, speaker=0),
            Word(text=" H", start=14.98, end=15.04, speaker=0),
            Word(text=" of", start=15.04, end=15.16, speaker=0),
            Word(text=" you,", start=15.16, end=15.26, speaker=0),
            Word(text=" maybe.", start=15.28, end=15.34, speaker=0),
            Word(text=" you", start=15.36, end=15.52, speaker=0),
            Word(text=" can", start=15.52, end=15.62, speaker=0),
            Word(text=" introduce", start=15.62, end=15.98, speaker=0),
            Word(text=" yourself", start=15.98, end=16.42, speaker=0),
            Word(text=" to", start=16.42, end=16.68, speaker=0),
            Word(text=" the", start=16.68, end=16.72, speaker=0),
            Word(text=" team", start=16.72, end=17.52, speaker=0),
            Word(text=" quickly", start=17.87, end=18.65, speaker=0),
            Word(text=" and", start=18.65, end=19.63, speaker=0),
            Word(text=" Oh,", start=20.91, end=21.55, speaker=0),
            Word(text=" this", start=21.67, end=21.83, speaker=0),
            Word(text=" is", start=21.83, end=22.17, speaker=0),
            Word(text=" a", start=22.17, end=22.35, speaker=0),
            Word(text=" reflector", start=22.35, end=22.89, speaker=0),
            Word(text=" translating", start=22.89, end=23.33, speaker=0),
            Word(text=" into", start=23.33, end=23.73, speaker=0),
            Word(text=" French", start=23.73, end=23.95, speaker=0),
            Word(text=" for", start=23.95, end=24.15, speaker=0),
            Word(text=" me.", start=24.15, end=24.43, speaker=0),
            Word(text=" This", start=27.87, end=28.19, speaker=0),
            Word(text=" is", start=28.19, end=28.45, speaker=0),
            Word(text=" all", start=28.45, end=28.79, speaker=0),
            Word(text=" the", start=28.79, end=29.15, speaker=0),
            Word(text=" way,", start=29.15, end=29.15, speaker=0),
            Word(text=" please,", start=29.53, end=29.59, speaker=0),
            Word(text=" please,", start=29.73, end=29.77, speaker=0),
            Word(text=" please,", start=29.77, end=29.83, speaker=0),
            Word(text=" please.", start=29.83, end=29.97, speaker=0),
            Word(text=" Yeah,", start=29.97, end=30.17, speaker=0),
            Word(text=" that's", start=30.25, end=30.33, speaker=0),
            Word(text=" all", start=30.33, end=30.49, speaker=0),
            Word(text=" it's", start=30.49, end=30.69, speaker=0),
            Word(text=" right.", start=30.69, end=30.69, speaker=0),
            Word(text=" Right.", start=30.72, end=30.98, speaker=1),
            Word(text=" Yeah,", start=31.56, end=31.72, speaker=2),
            Word(text=" that's", start=31.86, end=31.98, speaker=2),
            Word(text=" right.", start=31.98, end=32.2, speaker=2),
            Word(text=" Because", start=32.38, end=32.46, speaker=0),
            Word(text=" I", start=32.46, end=32.58, speaker=0),
            Word(text=" thought", start=32.58, end=32.78, speaker=0),
            Word(text=" I'd", start=32.78, end=33.0, speaker=0),
            Word(text=" be", start=33.0, end=33.02, speaker=0),
            Word(text=" able", start=33.02, end=33.18, speaker=0),
            Word(text=" to", start=33.18, end=33.34, speaker=0),
            Word(text=" pull", start=33.34, end=33.52, speaker=0),
            Word(text=" out.", start=33.52, end=33.68, speaker=0),
            Word(text=" Yeah,", start=33.7, end=33.9, speaker=0),
            Word(text=" that", start=33.9, end=34.02, speaker=0),
            Word(text=" was", start=34.02, end=34.24, speaker=0),
            Word(text=" the", start=34.24, end=34.34, speaker=0),
            Word(text=" one", start=34.34, end=34.44, speaker=0),
            Word(text=" before", start=34.44, end=34.7, speaker=0),
            Word(text=" that.", start=34.7, end=35.24, speaker=0),
            Word(text=" Friends,", start=35.84, end=36.46, speaker=0),
            Word(text=" if", start=36.64, end=36.7, speaker=0),
            Word(text=" you", start=36.7, end=36.7, speaker=0),
            Word(text=" have", start=36.7, end=37.24, speaker=0),
            Word(text=" tell", start=37.24, end=37.44, speaker=0),
            Word(text=" us", start=37.44, end=37.68, speaker=0),
            Word(text=" if", start=37.68, end=37.82, speaker=0),
            Word(text=" it's", start=37.82, end=38.04, speaker=0),
            Word(text=" good,", start=38.04, end=38.58, speaker=0),
            Word(text=" exceptionally", start=38.96, end=39.1, speaker=0),
            Word(text=" good", start=39.1, end=39.6, speaker=0),
            Word(text=" and", start=39.6, end=39.86, speaker=0),
            Word(text=" tell", start=39.86, end=40.0, speaker=0),
            Word(text=" us", start=40.0, end=40.06, speaker=0),
            Word(text=" when", start=40.06, end=40.2, speaker=0),
            Word(text=" it's", start=40.2, end=40.34, speaker=0),
            Word(text=" exceptionally", start=40.34, end=40.6, speaker=0),
            Word(text=" bad.", start=40.6, end=40.94, speaker=0),
            Word(text=" We", start=40.96, end=41.26, speaker=0),
            Word(text=" don't", start=41.26, end=41.44, speaker=0),
            Word(text=" need", start=41.44, end=41.66, speaker=0),
            Word(text=" that", start=41.66, end=41.82, speaker=0),
            Word(text=" at", start=41.82, end=41.94, speaker=0),
            Word(text=" the", start=41.94, end=41.98, speaker=0),
            Word(text=" middle", start=41.98, end=42.18, speaker=0),
            Word(text=" of", start=42.18, end=42.36, speaker=0),
            Word(text=" age.", start=42.36, end=42.7, speaker=0),
            Word(text=" Okay,", start=43.26, end=43.44, speaker=0),
            Word(text=" yeah,", start=43.68, end=43.76, speaker=0),
            Word(text=" that", start=43.78, end=44.3, speaker=0),
            Word(text=" sentence", start=44.3, end=44.72, speaker=0),
            Word(text=" right", start=44.72, end=45.1, speaker=0),
            Word(text=" before.", start=45.1, end=45.56, speaker=0),
            Word(text=" it", start=46.08, end=46.36, speaker=0),
            Word(text=" realizing", start=46.36, end=47.0, speaker=0),
            Word(text=" that", start=47.0, end=47.28, speaker=0),
            Word(text=" I", start=47.28, end=47.28, speaker=0),
            Word(text=" was", start=47.28, end=47.64, speaker=0),
            Word(text=" saying", start=47.64, end=48.06, speaker=0),
            Word(text=" that", start=48.06, end=48.44, speaker=0),
            Word(text=" it's", start=48.44, end=48.54, speaker=0),
            Word(text=" interesting", start=48.54, end=48.78, speaker=0),
            Word(text=" that", start=48.78, end=48.96, speaker=0),
            Word(text=" it's", start=48.96, end=49.08, speaker=0),
            Word(text=" translating", start=49.08, end=49.32, speaker=0),
            Word(text=" the", start=49.32, end=49.56, speaker=0),
            Word(text=" French", start=49.56, end=49.76, speaker=0),
            Word(text=" was", start=49.76, end=50.16, speaker=0),
            Word(text=" completely", start=50.16, end=50.4, speaker=0),
            Word(text=" wrong.", start=50.4, end=50.7, speaker=0),
        ]
    )

    segments = transcript.as_segments()
    assert len(segments) == 7

    # check speaker order
    assert segments[0].speaker == 0
    assert segments[1].speaker == 0
    assert segments[2].speaker == 0
    assert segments[3].speaker == 1
    assert segments[4].speaker == 2
    assert segments[5].speaker == 0
    assert segments[6].speaker == 0

    # check the timing (first entry, and first of others speakers)
    assert segments[0].start == 5.12
    assert segments[3].start == 30.72
    assert segments[4].start == 31.56
    assert segments[5].start == 32.38


def test_processor_transcript_segment_multitrack_interleaved():
    """Test as_segments(is_multitrack=True) with interleaved speakers.

    Multitrack recordings have words from different speakers sorted by start time,
    causing frequent speaker alternation. The multitrack mode should group by
    speaker first, then split into sentences.
    """
    from reflector.processors.types import Transcript, Word

    # Simulate real multitrack data: words sorted by start time, speakers interleave
    # Speaker 0 says: "Hello there."
    # Speaker 1 says: "I'm good."
    # When sorted by time, words interleave
    transcript = Transcript(
        words=[
            Word(text="Hello ", start=0.0, end=0.5, speaker=0),
            Word(text="I'm ", start=0.5, end=0.8, speaker=1),
            Word(text="there.", start=0.5, end=1.0, speaker=0),
            Word(text="good.", start=1.0, end=1.5, speaker=1),
        ]
    )

    # Default behavior (is_multitrack=False): breaks on every speaker change = 4 segments
    segments_default = transcript.as_segments(is_multitrack=False)
    assert len(segments_default) == 4

    # Multitrack behavior: groups by speaker, then sentences = 2 segments
    segments_multitrack = transcript.as_segments(is_multitrack=True)
    assert len(segments_multitrack) == 2

    # Check content - sorted by start time
    assert segments_multitrack[0].speaker == 0
    assert segments_multitrack[0].text == "Hello there."
    assert segments_multitrack[0].start == 0.0
    assert segments_multitrack[0].end == 1.0

    assert segments_multitrack[1].speaker == 1
    assert segments_multitrack[1].text == "I'm good."
    assert segments_multitrack[1].start == 0.5
    assert segments_multitrack[1].end == 1.5


def test_processor_transcript_segment_multitrack_overlapping_timestamps():
    """Test multitrack with exactly overlapping timestamps (real Daily.co data pattern)."""
    from reflector.processors.types import Transcript, Word

    # Real pattern from transcript 38d84d57: words with identical timestamps
    transcript = Transcript(
        words=[
            Word(text="speaking ", start=6.71, end=7.11, speaker=0),
            Word(text="Speaking ", start=6.71, end=7.11, speaker=1),
            Word(text="at ", start=7.11, end=7.27, speaker=0),
            Word(text="at ", start=7.11, end=7.27, speaker=1),
            Word(text="the ", start=7.27, end=7.43, speaker=0),
            Word(text="the ", start=7.27, end=7.43, speaker=1),
            Word(text="same ", start=7.43, end=7.59, speaker=0),
            Word(text="same ", start=7.43, end=7.59, speaker=1),
            Word(text="time.", start=7.59, end=8.0, speaker=0),
            Word(text="time.", start=7.59, end=8.0, speaker=1),
        ]
    )

    # Default: 10 segments (one per speaker change)
    segments_default = transcript.as_segments(is_multitrack=False)
    assert len(segments_default) == 10

    # Multitrack: 2 segments (one per speaker sentence)
    segments_multitrack = transcript.as_segments(is_multitrack=True)
    assert len(segments_multitrack) == 2

    # Both should have complete sentences
    assert "speaking at the same time." in segments_multitrack[0].text
    assert "Speaking at the same time." in segments_multitrack[1].text
