import asyncio
import sys
import signal

async def run_with_timeout():
    # Set up timeout handler
    def timeout_handler(signum, frame):
        print("\n=== Test timed out after 30 seconds ===")
        sys.exit(1)
    
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(30)  # 30 second timeout
    
    try:
        # Import after setting up timeout
        from reflector.processors.summary.summary_builder import main
        
        # Backup original argv
        original_argv = sys.argv[:]
        
        # Set up arguments
        sys.argv = ['summary_builder.py', 'test_transcript.txt', '--summary', '--participants']
        
        print("=== Starting Summary Builder Test ===")
        print(f"Processing: {sys.argv[1]}")
        print(f"Options: {sys.argv[2:]}")
        print("=" * 50)
        
        # Run the main function
        await main()
        
        print("\n=== Test completed successfully ===")
        
    except Exception as e:
        print(f"\n=== Error during test: {type(e).__name__}: {e} ===")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Cancel the alarm
        signal.alarm(0)
        # Restore argv
        sys.argv = original_argv

if __name__ == "__main__":
    asyncio.run(run_with_timeout())
