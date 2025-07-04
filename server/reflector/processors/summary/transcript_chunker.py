
import asyncio
from typing import List, Dict, Any, Optional, Callable, Awaitable
import structlog


def find_natural_split_point(text: str, target_pos: int, min_pos: int) -> int:
    """
    Find a natural place to split text near target_pos.
    
    Args:
        text: Text to split
        target_pos: Desired split position
        min_pos: Minimum acceptable split position
    
    Returns:
        Actual split position (between min_pos and target_pos)
    """
    if target_pos <= min_pos:
        return target_pos
    
    search_window = min(200, target_pos - min_pos)
    
    # Paragraph breaks
    for i in range(target_pos, max(min_pos, target_pos - search_window), -1):
        if i < len(text) - 1 and text[i:i+2] == '\n\n':
            return i + 2  # After the paragraph break
    
    # Speaker changes assuming format "Speaker: text"
    for i in range(target_pos, max(min_pos, target_pos - search_window), -1):
        if i > 0 and text[i-1] == '\n' and ':' in text[i:i+50]:
            return i
    
    # Sentence endings
    for i in range(target_pos, max(min_pos, target_pos - search_window), -1):
        if i < len(text) and text[i] in '.!?' and i < len(text) - 1 and text[i+1] == ' ':
            return i + 1
    
    # Line breaks
    for i in range(target_pos, max(min_pos, target_pos - search_window), -1):
        if i < len(text) and text[i] == '\n':
            return i + 1
    
    # Word boundaries
    for i in range(target_pos, max(min_pos, target_pos - search_window), -1):
        if i < len(text) and text[i] in ' \t':
            return i + 1
    
    # Fallback to target position
    return target_pos


async def process_transcript_with_template_aware_chunking(
    transcript: str,
    messages_template,
    max_context_tokens: int,
    llm_completion_func: Callable[..., Awaitable[str]], # str being json - accepts (messages, **kwargs)
    create_prompt_func: Callable[[str], str],
    validate_json_func: Callable,
    create_dedup_prompt_func: Optional[Callable[[str], str]] = None,  # Function for deduplication prompt
    overlap_ratio: float = 0.15,
    safety_margin_tokens: int = 50,
    logger: Optional[structlog.BoundLogger] = None
) -> List[str]:
    """
    Complete workflow: measure template, chunk transcript, process chunks, merge results.
    
    This function handles the entire chunking process while ensuring proper token accounting.
    
    Args:
        transcript: Full transcript text
        messages_template: Template Messages object (for measuring template overhead)
        max_context_tokens: Maximum context size (e.g., 160k tokens)
        llm_completion_func: Function to call LLM
        create_prompt_func: Function that takes transcript text and returns complete prompt
        validate_json_func: Function to validate JSON responses
        create_dedup_prompt_func: Optional function for deduplication prompt (takes subjects list)
        overlap_ratio: Fraction of chunk to overlap (0.0 - 0.5)
        safety_margin_tokens: Additional safety buffer
        logger: Optional logger
    
    Returns:
        List of consolidated subjects from all chunks
    """
    if logger is None:
        logger = structlog.get_logger()
    
    if not transcript or not transcript.strip():
        return []
    
    # Measure template overhead using the exact template structure
    template_copy = messages_template.copy()
    empty_prompt = create_prompt_func("")
    template_copy.add_user(empty_prompt)
    template_overhead_tokens = template_copy.count_tokens()
    
    logger.debug(f"Template overhead: {template_overhead_tokens} tokens")
    
    if template_overhead_tokens >= max_context_tokens:
        raise ValueError(f"Template overhead ({template_overhead_tokens}) exceeds context limit ({max_context_tokens})")
    
    # Calculate available space for transcript content
    max_content_tokens = max_context_tokens - template_overhead_tokens - safety_margin_tokens
    
    if max_content_tokens <= 0:
        raise ValueError("No space left for transcript content after template overhead")
    
    if not (0 <= overlap_ratio < 0.5):
        raise ValueError("overlap_ratio must be between 0 and 0.5")
    
    # Check if chunking is needed
    tokenizer = messages_template.tokenizer
    total_transcript_tokens = len(tokenizer.tokenize(transcript))
    
    if total_transcript_tokens <= max_content_tokens:
        logger.debug("Transcript fits in single chunk, no chunking needed")
        return await _process_chunk(
            transcript, messages_template, llm_completion_func,
            create_prompt_func, validate_json_func, logger
        )


    overlap_tokens = int(max_content_tokens * overlap_ratio)
    core_content_tokens = max_content_tokens - (2 * overlap_tokens)
    
    if core_content_tokens <= 0:
        raise ValueError("Content space too small for specified overlap ratio")
    
    logger.debug(f"Chunking: max_content={max_content_tokens}, core={core_content_tokens}, overlap={overlap_tokens}")
    
    chunks = _generate_chunks_with_overlap(
        transcript, tokenizer, core_content_tokens, overlap_tokens, logger
    )
    
    validated_chunks = []
    for i, chunk in enumerate(chunks):
        # Test actual token count with template
        test_messages = messages_template.copy()
        test_prompt = create_prompt_func(chunk)
        test_messages.add_user(test_prompt)
        actual_tokens = test_messages.count_tokens()

        # character-to-token estimation still could produce this case because density of tokens isn't uniform across text
        if actual_tokens > max_context_tokens:
            logger.warning(f"Chunk {i} too large ({actual_tokens} tokens), shrinking...")

            chunk = _shrink_chunk_to_fit(
                chunk, messages_template, create_prompt_func,
                max_context_tokens, logger
            )
        
        validated_chunks.append(chunk)
        logger.debug(f"Chunk {i}: {len(chunk)} chars, {actual_tokens} tokens")
    
    logger.debug(f"Processing {len(validated_chunks)} chunks in parallel")
    
    chunk_tasks = []
    for i, chunk in enumerate(validated_chunks):
        task = _process_chunk(
            chunk, messages_template, llm_completion_func,
            create_prompt_func, validate_json_func, logger
        )
        chunk_tasks.append(task)
    
    chunk_results = await asyncio.gather(*chunk_tasks, return_exceptions=True)
    
    all_subjects = []

    for i, result in enumerate(chunk_results):
        if isinstance(result, Exception):
            logger.error(f"Chunk {i} failed: {result}")
            continue
        if isinstance(result, list):
            all_subjects.extend(result)
        else:
            logger.warning(f"Chunk {i} returned unexpected result: {result}")
    
    logger.info(f"Collected {len(all_subjects)} subjects from chunks")
    
    # Deduplicate
    if len(validated_chunks) > 1 and len(all_subjects) > 3 and create_dedup_prompt_func:
        try:
            deduplicated = await _deduplicate_subjects(
                all_subjects, messages_template, llm_completion_func,
                create_dedup_prompt_func, validate_json_func, logger
            )
            return deduplicated
        except Exception as e:
            logger.error(f"Deduplication failed: {e}, returning basic dedupe")
            return list(dict.fromkeys(all_subjects))  # Basic deduplication
    
    return all_subjects


def _generate_chunks_with_overlap(
    transcript: str,
    tokenizer,
    core_content_tokens: int,
    overlap_tokens: int,
    logger: structlog.BoundLogger
) -> List[str]:
    """Generate overlapping chunks based on token estimates."""
    
    # Estimate characters per token
    total_tokens = len(tokenizer.tokenize(transcript))
    avg_chars_per_token = len(transcript) / total_tokens if total_tokens > 0 else 4.0
    
    # Apply safety margin to estimates
    safety_margin = 0.85
    core_chars = int(core_content_tokens * avg_chars_per_token * safety_margin)
    overlap_chars = int(overlap_tokens * avg_chars_per_token * safety_margin)
    
    chunks = []
    current_pos = 0
    chunk_count = 0
    max_chunks = 50  # Safety limit
    
    while current_pos < len(transcript) and chunk_count < max_chunks:
        # Calculate chunk boundaries. no leading overlap
        chunk_start = max(0, current_pos - overlap_chars)
        # no ending overlap
        chunk_end = min(len(transcript), current_pos + core_chars + overlap_chars)
        
        # Find natural split point
        chunk_end = find_natural_split_point(transcript, chunk_end, current_pos + core_chars)
        
        # Extract chunk
        chunk_content = transcript[chunk_start:chunk_end]
        
        if chunk_content.strip():  # Only add non-empty chunks
            chunks.append(chunk_content)
        
        # Move to next chunk position
        current_pos += core_chars
        chunk_count += 1
        
        # Ensure progress
        if chunk_end <= chunk_start + 100:
            current_pos = chunk_start + 100
    
    if chunk_count >= max_chunks:
        logger.warning(f"Hit maximum chunk limit ({max_chunks})")
    
    return chunks


def _shrink_chunk_to_fit(
    chunk: str,
    messages_template,
    create_prompt_func: Callable,
    max_context_tokens: int,
    logger: structlog.BoundLogger,
    max_attempts: int = 10
) -> str:
    """Shrink a chunk until it fits within context limits."""
    
    current_chunk = chunk
    attempts = 0
    
    while attempts < max_attempts:
        # Test current chunk size
        test_messages = messages_template.copy()
        test_prompt = create_prompt_func(current_chunk)
        test_messages.add_user(test_prompt)
        actual_tokens = test_messages.count_tokens()
        
        if actual_tokens <= max_context_tokens:
            break
        
        # Shrink by 10%
        shrink_amount = max(1, len(current_chunk) // 10)
        current_chunk = current_chunk[:-shrink_amount]
        attempts += 1
    
    if attempts >= max_attempts:
        logger.error(f"Could not shrink chunk to fit after {max_attempts} attempts")
    
    return current_chunk


async def _process_chunk(
    transcript: str,
    messages_template,
    llm_completion_func: Callable[..., Awaitable[str]],
    create_prompt_func: Callable,
    validate_json_func: Callable,
    logger: structlog.BoundLogger
) -> List[str]:

    messages = messages_template.copy()
    prompt = create_prompt_func(transcript)
    messages.add_user(prompt)

    content = await llm_completion_func(messages.messages, logger=logger)

    subjects = validate_json_func(content)
    if not isinstance(subjects, list):
        raise ValueError(f"Invalid subjects: {subjects}, validate_json_func must return a list of subjects or raise an exception")
    return subjects


async def _deduplicate_subjects(
    all_subjects: List[str],
    messages_template,
    llm_completion_func: Callable[..., Awaitable[str]],
    create_dedup_prompt_func: Callable,
    validate_json_func: Callable,
    logger: structlog.BoundLogger
) -> List[str]:
    """Deduplicate subjects using LLM."""
    
    messages = messages_template.copy()
    subjects_md = '\n'.join([f"- {subject}" for subject in all_subjects])
    
    # Use a different system message for deduplication
    messages.messages = [msg for msg in messages.messages if msg['role'] != 'user']  # Remove any existing user messages
    
    prompt = create_dedup_prompt_func(subjects_md, logger=logger)
    messages.add_user(prompt)
    
    content = await llm_completion_func(messages.messages, logger=logger)
    
    consolidated_subjects = validate_json_func(content)
    
    if isinstance(consolidated_subjects, list):
        logger.info(f"Consolidated {len(all_subjects)} subjects into {len(consolidated_subjects)}")
        return consolidated_subjects
    else:
        logger.warning("LLM returned non-list result, falling back to basic deduplication")
        return list(dict.fromkeys(all_subjects))  # Preserves order, removes duplicates