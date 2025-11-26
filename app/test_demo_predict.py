#!/usr/bin/env python3
"""
Test script to verify demo agent prediction works
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_demo_agent_init():
    """Test demo agent initialization"""
    print("Testing DemoAgent initialization...")
    try:
        from app.backend.demo_agent import DemoAgent
        agent = DemoAgent(city_name="Shanghai", model_name="qwen2.5-7b", platform="SiliconFlow")
        print(f"✓ DemoAgent initialized successfully")
        print(f"  - City: {agent.city_name}")
        print(f"  - Model: {agent.model_name}")
        print(f"  - Platform: {agent.platform}")
        print(f"  - Test data users: {len(agent.test_data) if agent.test_data else 0}")
        return agent
    except Exception as e:
        print(f"✗ Failed to initialize DemoAgent: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_demo_agent_predict(agent):
    """Test demo agent prediction"""
    print("\nTesting DemoAgent prediction...")
    if agent is None or agent.test_data is None or len(agent.test_data) == 0:
        print("⚠ Skipping prediction test (no data available)")
        return False

    try:
        # Get first user and trajectory
        user_id = list(agent.test_data.keys())[0]
        traj_id = list(agent.test_data[user_id].keys())[0]

        print(f"  Running prediction for user={user_id}, traj={traj_id}")
        result = agent.predict(
            city_name="Shanghai",
            user_id=user_id,
            traj_id=traj_id,
            prompt_type="agent_move_v6"
        )

        print(f"✓ Prediction completed successfully")
        print(f"  - User ID: {result['user_id']}")
        print(f"  - Trajectory ID: {result['traj_id']}")
        print(f"  - Prediction venue: {result['prediction']['venue_id']}")
        print(f"  - Ground truth venue: {result['ground_truth']['venue_id']}")
        print(f"  - Explanation: {result['prediction']['explanation'][:100]}...")
        return True

    except Exception as e:
        print(f"✗ Prediction failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=" * 60)
    print("Testing Demo Agent with Fixed Constructor Calls")
    print("=" * 60)
    print()

    agent = test_demo_agent_init()
    print()

    if agent:
        success = test_demo_agent_predict(agent)
        print()

        if success:
            print("=" * 60)
            print("✓ All tests passed! Demo agent is working correctly")
            print("=" * 60)
            return 0
        else:
            print("=" * 60)
            print("⚠ Prediction test failed")
            print("=" * 60)
            return 1
    else:
        print("=" * 60)
        print("✗ Initialization failed")
        print("=" * 60)
        return 1

if __name__ == "__main__":
    sys.exit(main())
