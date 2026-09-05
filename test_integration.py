

import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def test_flask_api():
    """Test the Flask API endpoints"""
    # Read the port from .env rather than hardcoding it. Port 5000 is taken by the
    # AirPlay receiver on macOS, which answers 403 and makes this suite look broken.
    base_url = f"http://{os.getenv('FLASK_HOST', '127.0.0.1')}:{os.getenv('FLASK_PORT', '5001')}"

    print("🧪 Testing UNIfy Flask API Integration")
    print("=" * 50)

    # Test health check
    print("\n1. Testing health check endpoint...")
    try:
        response = requests.get(f"{base_url}/")
        if response.status_code == 200:
            data = response.json()
            print(f"Health check passed: {data['message']}")
        else:
            print(f" Health check failed: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("Cannot connect to Flask server. Make sure it's running on localhost:5000")
        print("Run: python app.py")
        return False
    except Exception as e:
        print(f"Health check error: {e}")
        return False

    # Test sample profile
    test_profile = {
        "mental_health": "ADHD",
        "physical_health": "None",
        "courses": "Computer Science",
        "gpa": 3.8,
        "severity": "moderate"
    }

    # Test main recommendations endpoint
    print("\n2. Testing recommendations endpoint...")
    try:
        response = requests.post(
            f"{base_url}/api/recommendations",
            json=test_profile,
            headers={"Content-Type": "application/json"}
        )

        if response.status_code == 200:
            data = response.json()
            print("Recommendations endpoint working")
            print(f"   Source: {data.get('source', 'unknown')}")
            print(f"   Success: {data.get('success', False)}")
            if data.get('needed_accommodations'):
                print(
                    f"   Accommodations: {len(data['needed_accommodations'])} found")
            if data.get('recommendations'):
                print(f"   Universities: {len(data['recommendations'])} found")
        else:
            print(f"Recommendations endpoint failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"Recommendations endpoint error: {e}")
        return False

    # Test the direct recommender endpoint
    print("\n3. Testing direct recommender endpoint...")
    try:
        response = requests.post(
            f"{base_url}/api/claude",
            json=test_profile,
            headers={"Content-Type": "application/json"}
        )

        if response.status_code == 200:
            data = response.json()
            print("Direct recommender endpoint working")
            print(f"   Source: {data.get('source', 'unknown')}")
            print(f"   Success: {data.get('success', False)}")
        else:
            print(f"Direct recommender endpoint failed: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"Direct recommender endpoint error: {e}")

    # Test API test endpoint
    print("\n4. Testing API test endpoint...")
    try:
        response = requests.get(f"{base_url}/api/test")
        if response.status_code == 200:
            data = response.json()
            print("Test endpoint working")
            print(f"   Message: {data.get('message', 'No message')}")
        else:
            print(f"Test endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"Test endpoint error: {e}")

    print("\nAPI Integration test completed!")
    return True


def test_direct_imports():
    """Test that the recommender imports and is grounded in real data."""
    print("\n🔧 Testing direct module imports...")

    try:
        from claude_recommender import ClaudeRecommender
        recommender = ClaudeRecommender()
        print(f"Recommender import successful "
              f"({len(recommender.matrix)} universities, {len(recommender.labels)} labels)")

        # The point of the grounded backend: it can only name schools in the dataset.
        known = set(recommender.matrix["university"])
        needs = recommender._rule_based_needs({"mental_health": "ADHD",
                                               "physical_health": "None",
                                               "severity": "moderate"})
        named = {u["name"] for u in recommender.rank(needs)}
        invented = named - known
        if invented:
            print(f"FAIL: recommended universities not in the dataset: {invented}")
        else:
            print(f"All {len(named)} recommended universities are in the dataset")
    except Exception as e:
        print(f"Recommender import failed: {e}")


if __name__ == "__main__":
    print("Starting UNIfy Integration Tests...")

    # Test imports first
    test_direct_imports()

    # Test API endpoints
    test_flask_api()

    print("\nAll tests completed!")
    print("\nNext steps:")
    print("1. Start the Flask server: python app.py")
    print("2. Start the React dev server: npm run dev")
    print("3. Test the full integration at http://localhost:5173")
