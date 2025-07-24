#\!/usr/bin/env python
import asyncio
import sys
import os

# Add timeout protection
import signal
def timeout_handler(signum, frame):
    print("\n=== Test timed out after 30 seconds ===")
    sys.exit(1)

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(30)  # 30 second timeout

print("=== Testing Dual LLM Implementation ===")

try:
    from reflector.llm import LLM
    from reflector.llm.openai_llm import OpenAILLM
    from reflector.settings import settings
    from reflector.processors.summary.summary_builder import SummaryBuilder
    
    print("✓ Imports successful")
    
    async def test():
        # Create both LLMs
        print("\n1. Creating LLM instances...")
        openai_llm = OpenAILLM(config_prefix="SUMMARY", settings=settings)
        print(f"   - OpenAI LLM: {openai_llm.__class__.__name__}")
        
        legacy_llm = LLM.get_instance()
        print(f"   - Legacy LLM: {legacy_llm.__class__.__name__}")
        
        # Create SummaryBuilder with both
        print("\n2. Creating SummaryBuilder with both LLMs...")
        builder = SummaryBuilder(openai_llm, legacy_llm=legacy_llm)
        print("   ✓ SummaryBuilder created successfully")
        
        # Verify the setup
        print("\n3. Verifying LLM configuration:")
        print(f"   - Main LLM instance: {builder.llm_instance.__class__.__name__}")
        print(f"   - Legacy LLM instance: {builder.legacy_llm.__class__.__name__}")
        print(f"   - Has tokenizer: {hasattr(builder.legacy_llm, 'tokenizer')}")
        print(f"   - Has structured output: {hasattr(builder.legacy_llm, 'has_structured_output')}")
        
        # Read test transcript
        print("\n4. Loading test transcript...")
        with open('test_transcript.txt', 'r') as f:
            transcript = f.read()
        print(f"   - Loaded {len(transcript)} characters")
        
        builder.set_transcript(transcript)
        
        # Test individual operations
        print("\n5. Testing operations:")
        
        print("   - Identifying participants...")
        await builder.identify_participants()
        print("     ✓ Participants identified")
        
        print("   - Identifying transcription type...")
        await builder.identify_transcription_type()
        print(f"     ✓ Type: {builder.transcription_type}")
        
        print("   - Generating summary (this may take a moment)...")
        await builder.generate_summary(only_subjects=True)
        print(f"     ✓ Found {len(builder.subjects)} subjects")
        
        print("\n6. Results:")
        print("   Subjects found:")
        for i, subject in enumerate(builder.subjects, 1):
            print(f"     {i}. {subject}")
        
        print("\n=== Test completed successfully\! ===")
        return True
        
    # Run the async test
    success = asyncio.run(test())
    sys.exit(0 if success else 1)
    
except Exception as e:
    print(f"\n=== Error: {type(e).__name__}: {e} ===")
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    signal.alarm(0)  # Cancel timeout
