"""Processing package for AgentMove.

This package contains data processing utilities:
- data: Dataset loading and trajectory processing
- download: Data download utilities
- osm_address_deploy: Local Nominatim address resolution
- osm_address_web: Web-based address resolution
- process_fsq_city_data: Foursquare data processing
- process_isp_shanghai: Shanghai ISP data processing
- trajectory_address_match: Address matching for trajectories
"""

from .data import Dataset

__all__ = [
    "Dataset",
]

