#!/usr/bin/env python3
"""
Quick test script to verify demo functionality
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_imports():
    """Test that all required packages can be imported"""
    print("Testing imports...")
    try:
        import fastapi
        print("  ✓ fastapi")
    except ImportError:
        print("  ✗ fastapi - run: pip install fastapi")
        return False

    try:
        import uvicorn
        print("  ✓ uvicorn")
    except ImportError:
        print("  ✗ uvicorn - run: pip install uvicorn")
        return False

    try:
        from app.backend import config
        print("  ✓ app.backend.config")
    except ImportError as e:
        print(f"  ✗ app.backend.config - {e}")
        return False

    try:
        from app.backend import demo_agent
        print("  ✓ app.backend.demo_agent")
    except ImportError as e:
        print(f"  ✗ app.backend.demo_agent - {e}")
        return False

    try:
        from app.backend import api
        print("  ✓ app.backend.api")
    except ImportError as e:
        print(f"  ✗ app.backend.api - {e}")
        return False

    return True


def test_file_structure():
    """Test that all necessary files exist"""
    print("\nTesting file structure...")
    required_files = [
        "app/__init__.py",
        "app/backend/__init__.py",
        "app/backend/api.py",
        "app/backend/demo_agent.py",
        "app/backend/config.py",
        "app/frontend/index.html",
        "app/frontend/static/css/style.css",
        "app/frontend/static/js/main.js",
        "app/README.md",
        "app/requirements.txt",
        "app/start_demo.sh",
    ]

    all_exist = True
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"  ✓ {file_path}")
        else:
            print(f"  ✗ {file_path} - missing")
            all_exist = False

    return all_exist


def test_config():
    """Test configuration loading"""
    print("\nTesting configuration...")
    try:
        from app.backend.config import DEMO_CONFIG
        print(f"  ✓ Config loaded")
        print(f"    - Host: {DEMO_CONFIG.get('host')}")
        print(f"    - Port: {DEMO_CONFIG.get('port')}")
        print(f"    - Default city: {DEMO_CONFIG.get('default_city')}")
        print(f"    - Default model: {DEMO_CONFIG.get('default_model')}")
        return True
    except Exception as e:
        print(f"  ✗ Failed to load config: {e}")
        return False


def test_api_initialization():
    """Test FastAPI app initialization"""
    print("\nTesting API initialization...")
    try:
        from app.backend.api import app
        print(f"  ✓ FastAPI app created")
        print(f"    - Title: {app.title}")
        print(f"    - Version: {app.version}")

        # List routes
        routes = [route.path for route in app.routes if hasattr(route, 'path')]
        print(f"    - Routes: {len(routes)} endpoints")
        for route in sorted(routes):
            print(f"      • {route}")

        return True
    except Exception as e:
        print(f"  ✗ Failed to initialize API: {e}")
        return False


def main():
    print("=" * 50)
    print("AgentMove Demo - Quick Test")
    print("=" * 50)
    print()

    results = []

    results.append(("File Structure", test_file_structure()))
    results.append(("Imports", test_imports()))
    results.append(("Configuration", test_config()))
    results.append(("API Initialization", test_api_initialization()))

    print("\n" + "=" * 50)
    print("Test Summary")
    print("=" * 50)

    all_passed = True
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status} - {test_name}")
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print("🎉 All tests passed! Demo is ready to run.")
        print()
        print("To start the demo, run:")
        print("  bash app/start_demo.sh")
        print()
        print("Then visit: http://localhost:8000")
        return 0
    else:
        print("⚠ Some tests failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
