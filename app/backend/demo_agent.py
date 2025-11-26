"""
Simplified Agent Wrapper for Web Demo
Provides a user-friendly interface to the AgentMove system
"""
import os
import sys
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from processing.data import Dataset
from models.llm_api import LLMWrapper
from models.world_model import SpatialWorld, SocialWorld
from models.personal_memory import Memory
from models.prompts import prompt_generator
from utils import extract_json, create_dir
from config import PROCESSED_DIR


class DemoAgent:
    """Simplified agent for web demo with caching and optimizations"""

    def __init__(self, city_name: str = "Shanghai", model_name: str = "qwen2.5-7b",
                 platform: str = "SiliconFlow", use_int_venue: bool = True):
        self.city_name = city_name
        self.model_name = model_name
        self.platform = platform
        self.use_int_venue = use_int_venue

        # Initialize components
        self.dataset = None
        self.test_data = None
        self.ground_data = None
        self.llm_model = None
        self.social_world = None  # Cached, initialized once
        self.memory_units = {}  # Cached per user

        # Cache
        self._trajectory_cache = {}
        self._sample_trajectories = None

        print(f"Initializing DemoAgent for {city_name}...")
        self._load_dataset()

    def _load_dataset(self):
        """Load and cache dataset"""
        try:
            # Use Shanghai_ISP for real data (has correct column names)
            # Shanghai_filtered.csv uses old column names (lon/lat instead of longitude/latitude)
            dataset_name = "Shanghai_ISP" if self.city_name == "Shanghai" else self.city_name

            self.dataset = Dataset(
                dataset_name=dataset_name,
                use_int_venue=self.use_int_venue,
                test_sample=50,  # Limit for demo
                save_dir=PROCESSED_DIR
            )
            self.test_data, self.ground_data = self.dataset.get_generated_datasets()
            print(f"✓ Loaded dataset with {len(self.test_data)} users")

            # Pre-sample some trajectories for quick access
            self._cache_sample_trajectories()

        except Exception as e:
            print(f"✗ Failed to load dataset: {e}")
            # Create mock data for demo purposes
            self._create_mock_data()

    def _cache_sample_trajectories(self):
        """Cache sample trajectories for UI display"""
        self._sample_trajectories = []
        count = 0
        for user_id in list(self.test_data.keys())[:10]:  # First 10 users
            user_data = self.test_data[user_id]
            for traj_id in list(user_data.keys())[:2]:  # First 2 trajectories per user
                traj_data = user_data[traj_id]
                self._sample_trajectories.append({
                    "user_id": user_id,
                    "traj_id": traj_id,
                    "length": len(traj_data.get("context_stays", [])),
                    "preview": self._get_trajectory_preview(traj_data)
                })
                count += 1
                if count >= 20:  # Limit total samples
                    break
            if count >= 20:
                break

    def _get_trajectory_preview(self, traj_data: Dict) -> Dict:
        """Get trajectory preview for UI"""
        context_stays = traj_data.get("context_stays", [])
        context_pos = traj_data.get("context_pos", [])

        if not context_stays or not context_pos:
            return {}

        # Get start, middle, end points
        points = []
        indices = [0, len(context_stays) // 2, -1] if len(context_stays) > 2 else [0, -1]

        for idx in indices:
            stay = context_stays[idx]
            pos = context_pos[idx]
            points.append({
                "time": stay[0],
                "category": stay[2] if len(stay) > 2 else "Unknown",
                "lat": pos[1],
                "lng": pos[0]
            })

        return {
            "points": points,
            "total_points": len(context_stays)
        }

    def _create_mock_data(self):
        """Create mock data when real data is unavailable"""
        print("Creating mock data for demo...")
        # Create some historical stays for user profile
        # Format: [hour, weekday, category, venue_id, admin, subdistrict, poi, street]
        historical_stays_long = [
            [8, "Monday", "Residence", 1, "Pudong", "Lujiazui", "Home", "Century Avenue"],
            [9, "Monday", "Office", 2, "Pudong", "Lujiazui", "Office Tower", "Yincheng Road"],
            [18, "Monday", "Residence", 1, "Pudong", "Lujiazui", "Home", "Century Avenue"],
            [8, "Tuesday", "Residence", 1, "Pudong", "Lujiazui", "Home", "Century Avenue"],
            [9, "Tuesday", "Office", 2, "Pudong", "Lujiazui", "Office Tower", "Yincheng Road"],
            [12, "Tuesday", "Restaurant", 4, "Pudong", "Lujiazui", "Restaurant Plaza", "Dongyuan Road"],
        ]

        self.test_data = {
            "demo_user_1": {
                "1": {
                    "context_stays": [
                        [8, "Wednesday", "Residence", 1, "Pudong", "Lujiazui", "Residential Building", "Century Avenue"],
                        [9, "Wednesday", "Office", 2, "Pudong", "Lujiazui", "Office Tower", "Yincheng Road"],
                        [12, "Wednesday", "Restaurant", 3, "Pudong", "Lujiazui", "Restaurant Plaza", "Dongyuan Road"],
                    ],
                    "context_pos": [
                        [121.4737, 31.2304],
                        [121.4990, 31.2397],
                        [121.4921, 31.2467],
                    ],
                    "context_addr": [
                        ["Pudong", "Lujiazui", "Residential Building", "Century Avenue"],
                        ["Pudong", "Lujiazui", "Office Tower", "Yincheng Road"],
                        ["Pudong", "Lujiazui", "Restaurant Plaza", "Dongyuan Road"],
                    ],
                    "target_stay": [18, "Wednesday", "<next_place_id>", "<next_place_address>"],
                    "historical_stays": historical_stays_long[-3:],  # Last 3 for context
                    "historical_pos": [
                        [121.4737, 31.2304],
                        [121.4990, 31.2397],
                        [121.4921, 31.2467],
                    ],
                    "historical_addr": [
                        ["Pudong", "Lujiazui", "Home", "Century Avenue"],
                        ["Pudong", "Lujiazui", "Office Tower", "Yincheng Road"],
                        ["Pudong", "Lujiazui", "Restaurant Plaza", "Dongyuan Road"],
                    ],
                    "historical_stays_long": historical_stays_long
                }
            }
        }
        self.ground_data = {
            "demo_user_1": {
                "1": {
                    "ground_stay": 2,
                    "ground_pos": [121.4990, 31.2397],
                    "ground_addr": "Office Building, Pudong"
                }
            }
        }
        self._cache_sample_trajectories()

    def get_available_datasets(self) -> List[Dict]:
        """Get list of available datasets"""
        datasets = []
        data_dir = Path(PROCESSED_DIR)

        if data_dir.exists():
            for city_file in data_dir.glob("*_test.json"):
                city_name = city_file.stem.replace("_AgentMove_test", "")
                datasets.append({
                    "name": city_name,
                    "available": True
                })

        # Add current city if not in list
        if not any(d["name"] == self.city_name for d in datasets):
            datasets.append({
                "name": self.city_name,
                "available": self.test_data is not None
            })

        return datasets

    def get_sample_trajectories(self, city_name: str, limit: int = 10) -> List[Dict]:
        """Get sample trajectories for display"""
        if city_name != self.city_name:
            # Would need to reload dataset for different city
            return []

        if self._sample_trajectories:
            return self._sample_trajectories[:limit]
        return []

    def get_trajectory_detail(self, city_name: str, user_id: str, traj_id: str) -> Dict:
        """Get detailed trajectory information"""
        if city_name != self.city_name or user_id not in self.test_data:
            raise ValueError(f"Trajectory not found: {city_name}/{user_id}/{traj_id}")

        user_data = self.test_data[user_id]
        if traj_id not in user_data:
            raise ValueError(f"Trajectory {traj_id} not found for user {user_id}")

        traj_data = user_data[traj_id]
        ground_truth = self.ground_data.get(user_id, {}).get(traj_id, {})

        # Format trajectory for visualization
        trajectory_points = []
        context_stays = traj_data.get("context_stays", [])
        context_pos = traj_data.get("context_pos", [])

        for i, stay in enumerate(context_stays):
            pos = context_pos[i] if i < len(context_pos) else [0, 0]
            trajectory_points.append({
                "timestamp": stay[0],
                "duration": stay[1] if len(stay) > 1 else 0,
                "category": stay[2] if len(stay) > 2 else "Unknown",
                "venue_id": stay[3] if len(stay) > 3 else None,
                "latitude": pos[1],
                "longitude": pos[0],
                "index": i
            })

        return {
            "user_id": user_id,
            "traj_id": traj_id,
            "trajectory_points": trajectory_points,
            "ground_truth": {
                "venue_id": ground_truth.get("ground_stay"),
                "latitude": ground_truth.get("ground_pos", [0, 0])[1],
                "longitude": ground_truth.get("ground_pos", [0, 0])[0],
                "address": ground_truth.get("ground_addr", "Unknown")
            },
            "metadata": {
                "total_points": len(trajectory_points),
                "has_historical": len(traj_data.get("historical_stays", [])) > 0
            }
        }

    def update_model(self, model_name: str, platform: str):
        """Update LLM model and platform"""
        if model_name != self.model_name or platform != self.platform:
            self.model_name = model_name
            self.platform = platform
            self.llm_model = None  # Will be recreated on next prediction
            print(f"Updated model to {model_name} on {platform}")

    def predict(self, city_name: str, user_id: Optional[str] = None,
                traj_id: Optional[str] = None, prompt_type: str = "agent_move_v6") -> Dict:
        """
        Run prediction for a trajectory

        Args:
            city_name: City name
            user_id: User ID (if None, picks random)
            traj_id: Trajectory ID (if None, picks random)
            prompt_type: Prompt type to use

        Returns:
            Prediction result dictionary
        """
        # Select random trajectory if not specified
        if user_id is None or user_id not in self.test_data:
            user_id = list(self.test_data.keys())[0]

        if traj_id is None or traj_id not in self.test_data[user_id]:
            traj_id = list(self.test_data[user_id].keys())[0]

        # Get trajectory data
        traj_data = self.test_data[user_id][traj_id]
        ground_truth = self.ground_data.get(user_id, {}).get(traj_id, {})

        # Initialize components if needed
        if self.llm_model is None:
            self.llm_model = LLMWrapper(self.model_name, self.platform)

        if self.social_world is None and self.dataset is not None:
            # SocialWorld is initialized once for all trajectories
            # Only initialize if we have a real dataset (not mock data)
            try:
                self.social_world = SocialWorld(
                    traj_dataset=self.dataset,
                    save_dir=PROCESSED_DIR,
                    city_name=self.city_name,
                    khop=1,
                    max_neighbors=10
                )
            except Exception as e:
                print(f"⚠ Failed to initialize SocialWorld: {e}")
                # Continue without social world

        # SpatialWorld is created per trajectory (not cached)
        # Create it with the specific trajectory data
        spatial_world = SpatialWorld(
            platform=self.platform,
            model_name=self.model_name,
            city_name=self.city_name,
            traj_seqs=traj_data,
            explore_num=5
        )

        if user_id not in self.memory_units:
            # Get historical stays for this user (from first trajectory)
            first_traj_id = list(self.test_data[user_id].keys())[0]
            know_stays = self.test_data[user_id][first_traj_id].get("historical_stays_long", [])
            context_stays = traj_data.get("context_stays", [])

            self.memory_units[user_id] = Memory(
                know_stays=know_stays,
                context_stays=context_stays,
                memory_lens=15
            )

        # Get module outputs
        spatial_info = spatial_world.get_world_info()
        memory_info = self.memory_units[user_id].read_memory(user_id, None)

        # Get social info if social world is available
        if self.social_world is not None:
            last_venue_id = traj_data["context_stays"][-1][3] if traj_data["context_stays"] else None
            history_points = [x[3] for x in traj_data["context_stays"]]
            social_info = self.social_world.get_world_info(last_venue_id, history_points, "address")
        else:
            social_info = {}  # Empty social info when not available

        # Generate prompt
        prompt_text = prompt_generator(
            traj_data, prompt_type, spatial_info, memory_info, social_info, {}
        )

        # Get LLM prediction
        try:
            pre_text = self.llm_model.get_response(prompt_text=prompt_text)
            output_json, prediction, reason = extract_json(pre_text, prediction_key="prediction")
        except Exception as e:
            print(f"Prediction failed: {e}")
            # Return example prediction on error
            prediction = ground_truth.get("ground_stay", "Unknown")
            reason = f"Prediction failed due to: {str(e)[:100]}"
            output_json = {}

        # Format result
        result = {
            "user_id": user_id,
            "traj_id": traj_id,
            "prompt_type": prompt_type,
            "model": f"{self.model_name} ({self.platform})",
            "context_trajectory": [
                {
                    "lat": pos[1],
                    "lng": pos[0],
                    "time": stay[0],
                    "category": stay[2] if len(stay) > 2 else "Unknown",
                    "venue_id": stay[3] if len(stay) > 3 else None
                }
                for stay, pos in zip(traj_data["context_stays"], traj_data["context_pos"])
            ],
            "prediction": {
                "venue_id": prediction,
                "explanation": reason
            },
            "ground_truth": {
                "venue_id": ground_truth.get("ground_stay"),
                "latitude": ground_truth.get("ground_pos", [0, 0])[1],
                "longitude": ground_truth.get("ground_pos", [0, 0])[0],
                "address": ground_truth.get("ground_addr", "Unknown")
            },
            "module_outputs": {
                "spatial_world": spatial_info,
                "memory": memory_info,
                "social_world": social_info
            },
            "prompt": prompt_text[:500] + "..." if len(prompt_text) > 500 else prompt_text,
            "raw_response": str(output_json)[:500] if output_json else ""
        }

        return result
