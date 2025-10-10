"""Stub data for Daily.co testing - Fish conversation"""

import re

from reflector.utils import generate_uuid4

# The fish argument text - 2 speakers arguing about eating fish
FISH_TEXT = """Fish for dinner are nothing wrong with you? There's nothing wrong with me. Wrong with you? Would you shut up? There's nothing wrong with me. I'm just trying to. There's nothing wrong with me. I'm trying to eat a fish. Wrong with you trying to eat a fish and it falls off the plate. Would you shut up? You're bothering me. More than a fish is bothering me. Would you shut up and leave me alone? What's your problem? I'm just trying to eat a fish is wrong with you. I'm only trying to eat a fish. Would you shut up? Wrong with you. There's nothing wrong with me. There's nothing wrong with me. Wrong with you. There's nothing wrong with me. Wrong with you. There's nothing wrong with me. Would you shut up and let me eat my fish? Wrong with you. Shut up! What is wrong with you? Would you just shut up? What's your problem? Would you shut up with you? What is wrong with you? Wrong with me? I'm just trying to get my attention. Did you shut up? You're bothering me. Would you shut up? You're beginning to bug me. What's your problem? Just trying to eat my fish. Stay on the plate. Would you shut up? Just trying to eat my fish.

I'm gonna hit you with my problem. You're worse than this fish. You're more of a problem than a fish. What's your problem? Would you shut up? Would you shut your mouth? I want to eat my fish. Shut up! I can't even think. What's your problem? Trying to eat my fish is wrong with you. I don't have a problem. What is wrong with you? I have a problem. What's your problem? I don't have a problem. Can't you hear me with you? Can't you hear me? I don't have a problem. I want to eat my fish. Your problem? Just want to eat. What is wrong with you? Shut up! What is wrong with you? You just shut up! What's your problem? What is wrong with you anyway? What is wrong with you? I won't stay on the plate. You shut up! What is wrong with you? Would you just shut up? Let me eat my fish. What's your problem? Shut up and leave me alone! I can't even think. Wrong with you. I don't have a problem. Problem? I don't have a problem. Wrong with you. I don't have a problem with you. That's your problem. Don't have a problem? I want to eat my fish.

What is wrong with you? What's your problem? Problem? I just want to eat my fish. Wrong with you. What's wrong with you? I don't have a problem. You shut up! What's wrong with you? Just shut up! What's wrong with you? Shut up! What is wrong with you? I'm trying to eat a fish. I'm trying to eat a fish and it falls off the plate. Would you shut up? What is wrong with you? Would you shut up? Is wrong with you? Would you just shut up? What is wrong with you? Would you just shut? Is wrong with you? What's your problem? You just shut. What is wrong with you? Trying to eat my fish. Would you be quiet? What's your problem? Would you just shut up? Eat my fish. I can't even eat it. Don't stay on the plate. What's your problem? Would you shut up? What is wrong with you? What is wrong with you? Would you just shut up? What's your problem? What is wrong with you? I'm gonna hit you with my fish if you don't shut up. What's your problem? Would you shut up? What's wrong with you? What is wrong? Shut up! What's your problem?"""


def parse_fish_text():
    """Parse fish text into words with timestamps and speakers.

    Returns a list of words: [{"text": str, "start": float, "end": float, "speaker": int}]

    Speaker assignment heuristic:
    - Speaker 0 (eating fish): "fish", "eat", "trying", "problem", "I"
    - Speaker 1 (annoying): "wrong with you", "shut up", "What's your problem"
    """

    # Split into sentences (rough)
    sentences = re.split(r"([.!?])", FISH_TEXT)

    # Reconstruct sentences with punctuation
    full_sentences = []
    for i in range(0, len(sentences) - 1, 2):
        if sentences[i].strip():
            full_sentences.append(
                sentences[i].strip()
                + (sentences[i + 1] if i + 1 < len(sentences) else "")
            )

    words = []
    current_time = 0.0

    for sentence in full_sentences:
        if not sentence.strip():
            continue

        # Determine speaker based on content
        sentence_lower = sentence.lower()

        # Speaker 1 patterns (annoying person)
        if any(
            p in sentence_lower
            for p in [
                "wrong with you",
                "shut up",
                "what's your problem",
                "what is wrong",
                "would you shut",
                "you shut",
            ]
        ):
            speaker = 1
        # Speaker 0 patterns (trying to eat)
        elif any(
            p in sentence_lower
            for p in [
                "i'm trying",
                "i'm just",
                "i want to eat",
                "eat my fish",
                "trying to eat",
                "nothing wrong with me",
                "i don't have a problem",
                "just trying",
                "leave me alone",
                "can't even",
                "i'm gonna hit",
            ]
        ):
            speaker = 0
        # Default: alternate or use context
        else:
            # For short phrases, guess based on keywords
            if "fish" in sentence_lower and "eat" in sentence_lower:
                speaker = 0
            elif "problem" in sentence_lower and "your" not in sentence_lower:
                speaker = 0
            else:
                speaker = 1

        # Split sentence into words
        sentence_words = sentence.split()
        for word in sentence_words:
            word_duration = 0.3 + (len(word) * 0.05)  # ~0.3-0.5s per word

            words.append(
                {
                    "text": word + " ",  # Add space
                    "start": current_time,
                    "end": current_time + word_duration,
                    "speaker": speaker,
                }
            )

            current_time += word_duration

    return words


def generate_fake_topics(words):
    """Generate fake topics from words.

    Splits into ~3 topics based on timestamp.
    """
    if not words:
        return []

    total_duration = words[-1]["end"]
    chunk_size = len(words) // 3

    topics = []

    for i in range(3):
        start_idx = i * chunk_size
        end_idx = (i + 1) * chunk_size if i < 2 else len(words)

        if start_idx >= len(words):
            break

        chunk_words = words[start_idx:end_idx]

        topic = {
            "id": generate_uuid4(),
            "title": f"Fish Argument Part {i+1}",
            "summary": f"Argument about eating fish continues (part {i+1})",
            "timestamp": chunk_words[0]["start"],
            "duration": chunk_words[-1]["end"] - chunk_words[0]["start"],
            "transcript": "".join(w["text"] for w in chunk_words),
            "words": chunk_words,
        }

        topics.append(topic)

    return topics


def generate_fake_participants():
    """Generate fake participants."""
    return [
        {"id": generate_uuid4(), "speaker": 0, "name": "Fish Eater"},
        {"id": generate_uuid4(), "speaker": 1, "name": "Annoying Person"},
    ]


def get_stub_transcript_data():
    """Get complete stub transcript data for Daily.co testing.

    Returns dict with topics, participants, title, summaries, duration.
    """
    words = parse_fish_text()
    topics = generate_fake_topics(words)
    participants = generate_fake_participants()

    return {
        "topics": topics,
        "participants": participants,
        "title": "The Great Fish Eating Argument",
        "short_summary": "Two people argue about eating fish",
        "long_summary": "An extended argument between someone trying to eat fish and another person who won't stop asking what's wrong. The fish keeps falling off the plate.",
        "duration": words[-1]["end"] if words else 0.0,
    }
