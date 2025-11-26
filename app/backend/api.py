"""
AgentMove Web Demo - FastAPI Backend
Provides REST API for trajectory prediction visualization
"""
import os
import sys
import json
import logging
import traceback
from typing import List, Dict, Optional
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from app.backend.demo_agent import DemoAgent
from app.backend.config import DEMO_CONFIG

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AgentMove Demo API",
    description="Zero-shot next location prediction using LLM agents",
    version="1.0.0"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
frontend_dir = Path(__file__).parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=str(frontend_dir / "static")), name="static")

# Initialize demo agent
demo_agent = None


class PredictionRequest(BaseModel):
    """Request model for prediction"""
    city_name: str = "Shanghai"
    model_name: str = "qwen2.5-7b"
    platform: str = "SiliconFlow"
    prompt_type: str = "agent_move_v6"
    user_id: Optional[str] = None
    traj_id: Optional[str] = None
    num_samples: int = 5


class TrajectoryPoint(BaseModel):
    """Single trajectory point"""
    timestamp: str
    latitude: float
    longitude: float
    venue_id: Optional[int] = None
    category: Optional[str] = None
    address: Optional[str] = None


@app.on_event("startup")
async def startup_event():
    """Initialize demo agent on startup"""
    global demo_agent
    try:
        logger.info("Initializing demo agent...")
        demo_agent = DemoAgent(
            city_name=DEMO_CONFIG["default_city"],
            model_name=DEMO_CONFIG["default_model"],
            platform=DEMO_CONFIG["default_platform"]
        )
        logger.info("✓ Demo agent initialized successfully")
        print("✓ Demo agent initialized successfully")
    except Exception as e:
        logger.error(f"✗ Failed to initialize demo agent: {e}")
        logger.error(traceback.format_exc())
        print(f"✗ Failed to initialize demo agent: {e}")
        print("  Demo will run in limited mode")
        print(f"  Error details: {traceback.format_exc()}")


@app.get("/")
async def root():
    """Serve frontend homepage"""
    return FileResponse(str(frontend_dir / "index.html"))


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "agent_loaded": demo_agent is not None,
        "config": DEMO_CONFIG
    }


@app.get("/api/datasets")
async def get_datasets():
    """Get available datasets and cities"""
    if demo_agent is None:
        raise HTTPException(
            status_code=503,
            detail="Demo agent not initialized. Please check server logs."
        )

    try:
        logger.info("Fetching available datasets...")
        datasets = demo_agent.get_available_datasets()
        logger.info(f"Found {len(datasets)} datasets")
        return {
            "success": True,
            "datasets": datasets
        }
    except Exception as e:
        logger.error(f"Failed to get datasets: {e}")
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "message": "Failed to fetch datasets. Check server logs for details."
            }
        )


@app.get("/api/trajectories/{city_name}")
async def get_trajectories(city_name: str, limit: int = 10):
    """Get sample trajectories for a city"""
    if demo_agent is None:
        raise HTTPException(
            status_code=503,
            detail="Demo agent not initialized. Please check server logs."
        )

    try:
        logger.info(f"Fetching trajectories for {city_name}, limit={limit}")
        trajectories = demo_agent.get_sample_trajectories(city_name, limit)
        logger.info(f"Found {len(trajectories)} trajectories")
        return {
            "success": True,
            "city": city_name,
            "count": len(trajectories),
            "trajectories": trajectories
        }
    except Exception as e:
        logger.error(f"Failed to get trajectories: {e}")
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "message": f"Failed to fetch trajectories for {city_name}. Check server logs for details."
            }
        )


@app.get("/api/trajectory/{city_name}/{user_id}/{traj_id}")
async def get_trajectory_detail(city_name: str, user_id: str, traj_id: str):
    """Get detailed trajectory information"""
    if demo_agent is None:
        raise HTTPException(
            status_code=503,
            detail="Demo agent not initialized. Please check server logs."
        )

    try:
        logger.info(f"Fetching trajectory detail: {city_name}/{user_id}/{traj_id}")
        trajectory = demo_agent.get_trajectory_detail(city_name, user_id, traj_id)
        logger.info("Trajectory detail fetched successfully")
        return {
            "success": True,
            "trajectory": trajectory
        }
    except Exception as e:
        logger.error(f"Failed to get trajectory detail: {e}")
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "message": f"Failed to fetch trajectory {city_name}/{user_id}/{traj_id}. Check server logs for details."
            }
        )


@app.post("/api/predict")
async def predict_next_location(request: PredictionRequest):
    """Predict next location for a trajectory"""
    if demo_agent is None:
        logger.error("Demo agent not initialized")
        raise HTTPException(
            status_code=503,
            detail="Demo agent not initialized. Please check server logs."
        )

    try:
        logger.info(f"Prediction request: city={request.city_name}, user={request.user_id}, "
                   f"traj={request.traj_id}, model={request.model_name}, "
                   f"platform={request.platform}, prompt_type={request.prompt_type}")

        # Update agent configuration if needed
        if (request.model_name != demo_agent.model_name or
            request.platform != demo_agent.platform):
            logger.info(f"Updating agent model to {request.model_name} on {request.platform}")
            demo_agent.update_model(request.model_name, request.platform)

        # Run prediction
        logger.info("Running prediction...")
        result = demo_agent.predict(
            city_name=request.city_name,
            user_id=request.user_id,
            traj_id=request.traj_id,
            prompt_type=request.prompt_type
        )

        logger.info("Prediction completed successfully")
        return {
            "success": True,
            "prediction": result
        }
    except Exception as e:
        # Log the full error
        error_details = {
            "error_type": type(e).__name__,
            "error_message": str(e),
            "traceback": traceback.format_exc(),
            "request": {
                "city_name": request.city_name,
                "user_id": request.user_id,
                "traj_id": request.traj_id,
                "model_name": request.model_name,
                "platform": request.platform,
                "prompt_type": request.prompt_type
            }
        }

        logger.error(f"Prediction failed: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Full traceback:\n{traceback.format_exc()}")

        # Return detailed error to client
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "details": error_details,
                "message": "Prediction failed. Check server logs for details."
            }
        )


@app.get("/api/models")
async def get_available_models():
    """Get list of available LLM models"""
    return {
        "success": True,
        "platforms": {
            "SiliconFlow": ['qwen2.5-72b', 'qwen2.5-7b', 'qwen2-7b', 'glm4-9b', 'deepseekv2'],
            "DeepInfra": ['llama4-17b', 'llama3-8b', 'llama3-70b', 'gemma2-9b', 'mistral7bv3'],
            "OpenRouter": ['gpt35turbo', 'gpt4o', 'gpt4omini'],
        },
        "prompt_types": {
            "agent_move_v6": "AgentMove (Full Framework)",
            "llmmove": "LLM-Move Baseline",
            "llmzs": "LLM-ZS Baseline",
            "llmmob": "LLM-Mob Baseline"
        }
    }


@app.get("/api/example")
async def get_example_prediction():
    """Get a pre-computed example prediction for quick demo"""
    # This returns a cached example to show UI without API calls
    example = {
        "success": True,
        "is_example": True,
        "prediction": {
            "user_id": "example_user",
            "traj_id": "1",
            "context_trajectory": [
                {"lat": 31.2304, "lng": 121.4737, "time": "Mon Nov 25 08:30:00 2024", "venue": "Home"},
                {"lat": 31.2397, "lng": 121.4990, "time": "Mon Nov 25 09:15:00 2024", "venue": "Office"},
                {"lat": 31.2467, "lng": 121.4921, "time": "Mon Nov 25 12:30:00 2024", "venue": "Restaurant"},
            ],
            "predicted_location": {
                "lat": 31.2397,
                "lng": 121.4990,
                "venue": "Office",
                "confidence": 0.85
            },
            "ground_truth": {
                "lat": 31.2397,
                "lng": 121.4990,
                "venue": "Office"
            },
            "reasoning": "Based on the user's historical patterns, they typically return to office after lunch around 14:00. The spatial world model indicates this is a common location in the business district.",
            "memory_info": {
                "frequent_locations": ["Home", "Office", "Shopping Mall"],
                "typical_patterns": "Weekday: Home -> Office -> Restaurant -> Office -> Home"
            }
        }
    }
    return example


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api:app",
        host=DEMO_CONFIG.get("host", "0.0.0.0"),
        port=DEMO_CONFIG.get("port", 8000),
        reload=True
    )
