import re


def highlight_text(text: str, search_term: str) -> str:
    """Add ** markers around search term in text.
    
    Args:
        text: The text to highlight in
        search_term: The term to highlight
        
    Returns:
        Text with search term wrapped in ** markers
    """
    if not text or not search_term:
        return text or ""
    
    # Escape special regex characters in search term
    pattern = re.compile(re.escape(search_term), re.IGNORECASE)
    
    # Replace with highlighted version, preserving original case
    return pattern.sub(lambda m: f"**{m.group()}**", text)


def generate_snippet(transcript: dict, search_term: str, max_length: int = 150) -> str:
    """Find best snippet from transcript data.
    
    Priority order:
    1. Title (return full title if match)
    2. Short summary (with context)
    3. Long summary (with context)
    4. Topics transcript text (with context)
    
    Args:
        transcript: Dict with transcript data
        search_term: Term to search for
        max_length: Maximum snippet length
        
    Returns:
        Highlighted snippet or empty string if no match
    """
    if not search_term:
        return ""
    
    search_lower = search_term.lower()
    
    # Check title first (highest priority)
    title = transcript.get('title')
    if title and search_lower in title.lower():
        return highlight_text(title, search_term)
    
    # Then check summaries
    for field in ['short_summary', 'long_summary']:
        text = transcript.get(field)
        if text and search_lower in text.lower():
            # Find position and extract context
            pos = text.lower().find(search_lower)
            
            # Calculate context window
            context_before = 50
            context_after = 50
            
            start = max(0, pos - context_before)
            end = min(len(text), pos + len(search_term) + context_after)
            
            # Extract snippet
            snippet = text[start:end]
            
            # Add ellipsis if truncated (removed per user request)
            # if start > 0:
            #     snippet = "..." + snippet
            # if end < len(text):
            #     snippet = snippet + "..."
            
            return highlight_text(snippet, search_term)
    
    # Finally check topics
    topics = transcript.get('topics', [])
    for topic in topics:
        topic_text = topic.get('transcript')
        if topic_text and search_lower in topic_text.lower():
            pos = topic_text.lower().find(search_lower)
            
            context_before = 50
            context_after = 50
            
            start = max(0, pos - context_before)
            end = min(len(topic_text), pos + len(search_term) + context_after)
            
            snippet = topic_text[start:end]
            
            return highlight_text(snippet, search_term)
    
    # No match found
    return ""