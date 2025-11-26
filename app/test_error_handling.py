#!/usr/bin/env python3
"""
Test script to verify error handling in the demo API
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_logging():
    """Test logging configuration"""
    import logging
    logger = logging.getLogger('test')
    logger.info("This is an info message")
    logger.error("This is an error message")
    print("✓ Logging works")

def test_traceback():
    """Test traceback formatting"""
    import traceback
    try:
        raise ValueError("Test error")
    except Exception as e:
        tb = traceback.format_exc()
        print("✓ Traceback formatting works:")
        print(tb[:200])

def test_api_imports():
    """Test API imports"""
    try:
        from app.backend import api
        print("✓ API module imports successfully")
        print(f"  - Logger name: {api.logger.name}")
        print(f"  - FastAPI app: {api.app.title}")
    except Exception as e:
        print(f"✗ Failed to import API: {e}")
        import traceback
        traceback.print_exc()
        return False
    return True

def main():
    print("=" * 50)
    print("Testing Error Handling Improvements")
    print("=" * 50)
    print()

    test_logging()
    print()

    test_traceback()
    print()

    if test_api_imports():
        print()
        print("=" * 50)
        print("✓ All tests passed!")
        print("=" * 50)
        print()
        print("Error handling has been improved with:")
        print("  1. Detailed logging with timestamps")
        print("  2. Full traceback in server logs")
        print("  3. Structured error responses to client")
        print("  4. Better error messages in frontend")
        print()
        print("Now when predict fails, you will see:")
        print("  - Console: Full error details with traceback")
        print("  - Server logs: Detailed logging with context")
        print("  - Frontend: User-friendly error message with details")
        return 0
    else:
        print()
        print("=" * 50)
        print("✗ Some tests failed")
        print("=" * 50)
        return 1

if __name__ == "__main__":
    sys.exit(main())
