"""Configuration module for AgentMove.

This module provides centralized configuration management with:
- Logging setup
- Environment variable loading
- Path definitions
- API settings
"""

import logging
import os
from pathlib import Path

# =============================================================================
# Logging Configuration
# =============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# =============================================================================
# Environment Variables
# =============================================================================
# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / '.env'
    load_dotenv(dotenv_path=env_path)
    logger.info(f"Loaded environment variables from {env_path}")
except ImportError:
    logger.warning("python-dotenv not installed. Using system environment variables only.")
    logger.info("Install it with: pip install python-dotenv")
except Exception as e:
    logger.error(f"Failed to load .env file: {e}")

# =============================================================================
# Proxy Configuration
# =============================================================================
PROXY = os.environ.get("PROXY", "")  # Default: no proxy
if not PROXY:
    PROXY = None  # Set to None if empty string
elif PROXY and not PROXY.startswith(("http://", "https://", "socks5://")):
    # If PROXY is just IP:PORT, add http:// prefix
    PROXY = f"http://{PROXY}"

# =============================================================================
# Experiment Configuration
# =============================================================================
# EXP_CITIES = ['Tokyo', 'Nairobi', 'NewYork', 'Sydney', 'CapeTown', 'Paris', 'Beijing', 'Mumbai', 'SanFrancisco', 'London', 'SaoPaulo', 'Moscow']
# EXP_CITIES = ["Beijing"] # use it for quickly start
EXP_CITIES = ["Shanghai"]  # for WWW2019

# Dataset format (used by TIST2015 and WWW2019)
DATASET = 'TIST2015'

# =============================================================================
# Data Paths
# =============================================================================
DATA_PATH = "data/"
TIST2015_DATA_DIR = f"{DATA_PATH}dataset_tist2015"
TSMC2014_DATA_DIR = f"{DATA_PATH}dataset_tsmc2015"
GOWALLA_DATA_DIR = f"{DATA_PATH}dataset_gowalla"
WWW2019_DATA_DIR = f"{DATA_PATH}dataset_www2019"

# Temp Data - used for location address matching
NO_ADDRESS_TRAJ_DIR = "data/input_trajectories/"
NO_ADDRESS_WEIBO_TRAJ_DIR = f"{WWW2019_DATA_DIR}/input/"
NOMINATIM_PATH = 'data/nominatim/'
ADDRESS_L4_DIR = "data/address_L4/"

# Final processed data paths
CITY_DATA_DIR = "data/input_trajectories_clean/"
PROCESSED_DIR = "data/processed/"

# Results
SUMMARY_SAVE_DIR = "results/summary/"

# =============================================================================
# Nominatim Configuration
# =============================================================================
# IP:PORT e.g., 127.0.0.1:8080
NOMINATIM_DEPLOY_SERVER = os.environ.get("nominatim_deploy_server_address", "127.0.0.1:8080")
NOMINATIM_DEPLOY_WORKERS = 20  # Number of parallel workers for address matching

# Address formatting
ADDRESS_L4_FORMAT_MODEL = "llama3-8b"  # LLM used for 4-level address formatting
ADDRESS_L4_WORKERS = 50  # Number of parallel workers for address formatting

# =============================================================================
# API Retry Configuration
# =============================================================================
WAIT_TIME_MIN = 3
WAIT_TIME_MAX = 60
ATTEMPT_COUNTER = 10

# =============================================================================
# vLLM Configuration
# =============================================================================
VLLM_URL = os.environ.get("VLLM_URL", "http://localhost:8000/v1")

# =============================================================================
# Timezone Offsets (in minutes)
# =============================================================================
OFFSET_DICT = {
    'Tokyo': 540,
    'Moscow': 180,
    'SaoPaulo': -180,
    'Shanghai': 480,
    'Shanghai_ISP': 480,
    'Shanghai_Weibo': 480
}
