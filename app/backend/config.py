"""
Demo Configuration
Reads from .env file if available, otherwise uses defaults
"""
import os
from pathlib import Path

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Load from project root .env file
    env_path = Path(__file__).parent.parent.parent / '.env'
    load_dotenv(dotenv_path=env_path)
except ImportError:
    pass  # dotenv not installed, will use system env vars
except Exception:
    pass  # Failed to load .env, will use system env vars

DEMO_CONFIG = {
    # Server settings
    "host": os.environ.get("DEMO_HOST", "0.0.0.0"),
    "port": int(os.environ.get("DEMO_PORT", "8000")),

    # Default model settings
    "default_city": os.environ.get("DEMO_DEFAULT_CITY", "Shanghai"),
    "default_model": os.environ.get("DEMO_DEFAULT_MODEL", "qwen2.5-7b"),
    "default_platform": os.environ.get("DEMO_DEFAULT_PLATFORM", "SiliconFlow"),
    "default_prompt_type": "agent_move_v6",

    # Demo limits
    "max_trajectories": 50,
    "max_trajectory_length": 20,

    # UI settings
    "map_center": {
        "Shanghai": [31.2304, 121.4737],
        "Beijing": [39.9042, 116.4074],
        "Tokyo": [35.6762, 139.6503],
        "NewYork": [40.7128, -74.0060],
    },
    "map_zoom": 12,

    # Feature flags
    "enable_real_predictions": True,  # Set to False to use mock predictions only
    "cache_predictions": True,
    "show_module_details": True,
}
