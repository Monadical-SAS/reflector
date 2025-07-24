#\!/usr/bin/env python
import asyncio
import sys

print("=== Testing LLM Isolation ===")

try:
    from reflector.llm import LLM
    from reflector.llm.openai_llm import OpenAILLM
    from reflector.settings import settings
    from reflector.processors.summary.summary_builder import SummaryBuilder
    
    # Mock completion methods to track which LLM is called
    calls_log = []
    
    async def mock_openai_completion(self, messages, **kwargs):
        calls_log.append(("OpenAI", messages[0].get("role", ""), messages[0].get("content", "")[:50]))
        return {"choices": [{"message": {"content": '["Speaker 1", "Speaker 2", "Speaker 3"]'}}]}
    
    async def mock_legacy_completion(self, messages, **kwargs):
        calls_log.append(("Legacy", messages[0].get("role", ""), messages[0].get("content", "")[:50]))
        return {"choices": [{"message": {"content": '["Speaker 1", "Speaker 2", "Speaker 3"]'}}]}
    
    # Patch the completion methods
    OpenAILLM.completion = mock_openai_completion
    from reflector.llm.llm_modal import ModalLLM
    ModalLLM._completion = mock_legacy_completion
    
    async def test():
        print("\n1. Creating LLM instances...")
        openai_llm = OpenAILLM(config_prefix="SUMMARY", settings=settings)
        legacy_llm = LLM.get_instance()
        
        print("\n2. Creating SummaryBuilder...")
        builder = SummaryBuilder(openai_llm, legacy_llm=legacy_llm)
        
        # Simple test transcript
        builder.set_transcript("Speaker 1: Test meeting. Speaker 2: Agreed. Speaker 3: Let's proceed.")
        
        print("\n3. Testing different operations:")
        
        # Test identify_participants (should use Legacy LLM)
        print("\n   Testing identify_participants...")
        await builder.identify_participants()
        
        # Check what was called
        print("\n4. Checking LLM calls:")
        for llm_type, role, content in calls_log:
            print(f"   - {llm_type} LLM called with {role} message: '{content}...'")
        
        # Verify isolation
        print("\n5. Verification:")
        legacy_calls = [c for c in calls_log if c[0] == "Legacy"]
        openai_calls = [c for c in calls_log if c[0] == "OpenAI"]
        
        print(f"   - Legacy LLM calls: {len(legacy_calls)}")
        print(f"   - OpenAI LLM calls: {len(openai_calls)}")
        
        if len(legacy_calls) > 0 and len(openai_calls) == 0:
            print("\n✅ SUCCESS: identify_participants correctly used Legacy LLM only\!")
        else:
            print("\n❌ FAILED: LLM isolation not working correctly\!")
            
        return True
        
    asyncio.run(test())
    
except Exception as e:
    print(f"\n=== Error: {type(e).__name__}: {e} ===")
    import traceback
    traceback.print_exc()
    sys.exit(1)
