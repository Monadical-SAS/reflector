def clean_title(title: str) -> str:
    """
    Clean and format a title string for consistent capitalization.

    Rules:
    - Strip surrounding quotes (single or double)
    - Capitalize the first word
    - Capitalize words longer than 3 characters
    - Keep words with 3 or fewer characters lowercase (except first word)

    Args:
        title: The title string to clean

    Returns:
        The cleaned title with consistent capitalization

    Examples:
        >>> clean_title("hello world")
        "Hello World"
        >>> clean_title("meeting with the team")
        "Meeting With the Team"
        >>> clean_title("'Title with quotes'")
        "Title With Quotes"
    """
    title = title.strip("\"'")
    words = title.split()
    if words:
        words = [
            word.capitalize() if i == 0 or len(word) > 3 else word.lower()
            for i, word in enumerate(words)
        ]
        title = " ".join(words)
    return title
