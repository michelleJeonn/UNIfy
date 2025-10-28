"""
UNIfy Flask API Server
Provides REST API endpoints for the React frontend.
Simplified version without ML dependencies for first scope.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import logging
from typing import Dict, Any
from dotenv import load_dotenv
# Import Gemini lazily to avoid blocking server startup
# from gemini_recommender import get_gemini_recommendations

# Load environment variables from .env file
load_dotenv()


def validate_student_profile(data: dict):
    """Validate student profile data."""
    required_fields = ['mental_health', 'physical_health', 'courses', 'gpa', 'severity']
    missing = [f for f in required_fields if f not in data]
    if missing:
        return False, f"Missing required fields: {', '.join(missing)}"
    
    try:
        gpa = float(data['gpa'])
    except (TypeError, ValueError):
        return False, "GPA must be a valid number"
    
    if not 0.0 <= gpa <= 4.0:
        return False, "GPA must be between 0.0 and 4.0"
    
    if data['severity'] not in ['mild', 'moderate', 'severe']:
        return False, "Severity must be one of: mild, moderate, severe"
    
    return True, ""


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def error_response(message: str, status: int = 400, code: str = "BAD_REQUEST"):
    """Create standardized error response."""
    return jsonify({"success": False, "error": {"code": code, "message": message}}), status


def get_recommendations(student_profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get university recommendations using Gemini AI.
    Falls back to mock data if Gemini is not available.
    """
    try:
        # Try Gemini AI first (lazy import)
        try:
            from gemini_recommender import get_gemini_recommendations
            print("Attempting to call Gemini AI...")
            gemini_result = get_gemini_recommendations(student_profile)
            print(f"Gemini AI returned: {gemini_result}")
        except ImportError as e:
            print(f"Gemini import failed: {e}")
            gemini_result = {"success": False, "error": "Gemini not available"}
        
        if gemini_result.get("success", False):
            print("Using Gemini AI result")
            return gemini_result
        else:
            # Fallback to mock recommendations if Gemini fails
            print(f"Gemini AI failed: {gemini_result.get('error', 'Unknown error')}")
            print("Falling back to mock recommendations")
            mock_result = get_mock_recommendations(student_profile)
            print(f"Mock result: {mock_result}")
            return mock_result
            
    except Exception as e:
        print(f"Error getting recommendations: {str(e)}")
        print("Using mock recommendations due to error")
        mock_result = get_mock_recommendations(student_profile)
        print(f"Mock result: {mock_result}")
        return mock_result


def get_mock_recommendations(student_profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate mock university recommendations as fallback.
    """
    # Mock data for demonstration
    mock_universities = [
        {
            "name": "University of Toronto",
            "score": 4.3,
            "accessibility_rating": 4.5,
            "disability_support_rating": 4.7,
            "available_accommodations": ["Extended time", "Note-taking services", "Academic coaching"],
            "location": "Ontario",
            "reason": "Strong disability services and comprehensive support programs"
        },
        {
            "name": "University of British Columbia",
            "score": 4.1,
            "accessibility_rating": 4.2,
            "disability_support_rating": 4.4,
            "available_accommodations": ["Extended time", "Alternative testing formats", "Assistive technology"],
            "location": "British Columbia",
            "reason": "Excellent accessibility infrastructure and support services"
        },
        {
            "name": "McGill University",
            "score": 3.9,
            "accessibility_rating": 4.0,
            "disability_support_rating": 4.1,
            "available_accommodations": ["Extended time", "Note-taking services", "Priority registration"],
            "location": "Quebec",
            "reason": "Comprehensive disability support and accommodation services"
        }
    ]
    
    # Filter accommodations based on student profile
    accommodations = []
    if student_profile['mental_health'] != 'None':
        accommodations.extend(["Extended time", "Academic coaching", "Priority registration"])
    if student_profile['physical_health'] != 'None':
        accommodations.extend(["Assistive technology", "Accessible facilities", "Alternative testing formats"])
    
    # Add general accommodations
    accommodations.extend(["Note-taking services", "Counseling services"])
    accommodations = list(set(accommodations))  # Remove duplicates
    
    return {
        "success": True,
        "source": "mock_fallback",
        "needed_accommodations": accommodations,
        "recommendations": mock_universities
    }


# Initialize Flask app
app = Flask(__name__)
FRONTEND_ORIGINS = os.environ.get(
    "FRONTEND_ORIGINS", "http://localhost:5173,http://localhost:3000")
CORS(app, resources={r"/api/*": {"origins": FRONTEND_ORIGINS.split(",")}})

# Configuration
app.config['JSON_SORT_KEYS'] = False


@app.route('/', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'message': 'UNIfy API server is running',
        'version': '1.0.0',
        'endpoints': {
            'recommendations': '/api/recommendations',
            'health': '/',
            'test': '/api/test'
        }
    })


@app.route('/api/recommendations', methods=['POST'])
def get_university_recommendations():
    """
    Main API endpoint for getting university recommendations.

    Expected JSON payload:
    {
        "mental_health": "ADHD",
        "physical_health": "None", 
        "courses": "Computer Science",
        "gpa": 3.8,
        "severity": "moderate"
    }

    Returns:
    {
        "success": true,
        "source": "mock_recommendations",
        "needed_accommodations": ["Extended time", "Academic coaching"],
        "recommendations": [
            {
                "name": "University of Toronto",
                "score": 4.3,
                "accessibility_rating": 4.5,
                "disability_support_rating": 4.7,
                "available_accommodations": ["Extended time", "Note-taking services"],
                "location": "Ontario",
                "reason": "Strong disability services"
            }
        ]
    }
    """
    try:
        # Validate request
        if not request.is_json:
            return error_response("Request must be JSON", 400, "NOT_JSON")

        data = request.get_json()
        ok, msg = validate_student_profile(data)
        if not ok:
            return error_response(msg, 400, "VALIDATION_ERROR")

        student_profile = {
            'mental_health': str(data['mental_health']),
            'physical_health': str(data['physical_health']),
            'courses': str(data['courses']),
            'gpa': float(data['gpa']),
            'severity': str(data['severity'])
        }

        logger.info(f"Processing recommendation request for: {student_profile}")

        # Get recommendations (Gemini AI with fallback)
        print("=" * 60)
        print("CALLING GET_RECOMMENDATIONS FROM MAIN ENDPOINT")
        print("=" * 60)
        result = get_recommendations(student_profile)
        print("=" * 60)
        print("GET_RECOMMENDATIONS RESULT RECEIVED")
        print("=" * 60)
        print(f"Result: {result}")

        logger.info(f"Recommendation result: success={result['success']}, source={result.get('source', 'unknown')}")

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error in recommendations endpoint: {str(e)}")
        return error_response("Internal server error", 500, "INTERNAL_ERROR")


@app.route('/api/test', methods=['GET'])
def test_recommendations():
    """Test endpoint with sample data."""
    try:
        # Sample student profile for testing
        test_profile = {
            'mental_health': 'ADHD',
            'physical_health': 'None',
            'courses': 'Computer Science',
            'gpa': 3.8,
            'severity': 'moderate'
        }

        logger.info("Running test recommendation")
        result = get_recommendations(test_profile)

        return jsonify({
            'message': 'Test completed successfully',
            'test_profile': test_profile,
            'result': result
        })

    except Exception as e:
        logger.error(f"Error in test endpoint: {str(e)}")
        return error_response("Internal server error", 500, "INTERNAL_ERROR")


@app.route('/api/gemini', methods=['POST'])
def get_gemini_recommendations_endpoint():
    """
    Direct Gemini AI endpoint for testing.

    Expected JSON payload: same as /api/recommendations
    """
    try:
        if not request.is_json:
            return error_response("Request must be JSON", 400, "NOT_JSON")

        data = request.get_json()

        # Create student profile (same validation as main endpoint)
        required_fields = ['mental_health', 'physical_health', 'courses', 'gpa', 'severity']
        missing_fields = [field for field in required_fields if field not in data]

        if missing_fields:
            return error_response(f'Missing required fields: {", ".join(missing_fields)}', 400, "VALIDATION_ERROR")

        student_profile = {
            'mental_health': str(data['mental_health']),
            'physical_health': str(data['physical_health']),
            'courses': str(data['courses']),
            'gpa': float(data['gpa']),
            'severity': str(data['severity'])
        }

        logger.info(f"Processing Gemini AI request for: {student_profile}")

        # Get recommendations directly from Gemini AI (lazy import)
        try:
            from gemini_recommender import get_gemini_recommendations
            print("=" * 60)
            print("CALLING GEMINI AI FROM FLASK ENDPOINT")
            print("=" * 60)
            result = get_gemini_recommendations(student_profile)
            print("=" * 60)
            print("GEMINI AI RESULT RECEIVED")
            print("=" * 60)
            print(f"Result: {result}")
        except ImportError as e:
            print(f"Gemini import failed: {e}")
            result = {"success": False, "error": "Gemini not available"}

        logger.info(f"Gemini AI result: success={result['success']}, source={result.get('source', 'unknown')}")

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error in Gemini endpoint: {str(e)}")
        return error_response("Internal server error", 500, "INTERNAL_ERROR")


@app.route('/api/roadmap', methods=['POST'])
def get_university_roadmap():
    """
    Get detailed roadmap information for a specific university.
    
    Expected JSON payload:
    {
        "university_name": "University of Toronto",
        "student_profile": {
            "mental_health": "ADHD",
            "physical_health": "None",
            "courses": "Computer Science",
            "gpa": 3.8,
            "severity": "moderate"
        }
    }
    """
    try:
        if not request.is_json:
            return error_response("Request must be JSON", 400, "NOT_JSON")
        
        data = request.get_json()
        
        # Validate required fields
        if 'university_name' not in data:
            return error_response("Missing required field: university_name", 400, "VALIDATION_ERROR")
        
        if 'student_profile' not in data:
            return error_response("Missing required field: student_profile", 400, "VALIDATION_ERROR")
        
        university_name = data['university_name']
        student_profile = data['student_profile']
        
        # Validate student profile
        ok, msg = validate_student_profile(student_profile)
        if not ok:
            return error_response(f"Invalid student profile: {msg}", 400, "VALIDATION_ERROR")
        
        logger.info(f"Getting roadmap details for {university_name}")
        
        # Try to get roadmap details from Gemini AI
        try:
            from gemini_recommender import get_university_roadmap_details
            result = get_university_roadmap_details(university_name, student_profile)
        except ImportError:
            result = {
                "success": False,
                "error": "Gemini AI not available",
                "source": "gemini_ai"
            }
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in roadmap endpoint: {str(e)}")
        return error_response("Internal server error", 500, "INTERNAL_ERROR")


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return error_response("Endpoint not found", 404, "NOT_FOUND")


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    logger.error(f"Internal server error: {str(error)}")
    return error_response("Internal server error", 500, "INTERNAL_ERROR")


def create_app():
    """Application factory pattern."""
    return app


if __name__ == '__main__':
    # Get configuration from environment variables
    host = os.getenv('FLASK_HOST', '127.0.0.1')
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'

    logger.info(f"Starting UNIfy API server on {host}:{port}")
    logger.info(f"Debug mode: {debug}")

    # Print available endpoints
    print("\n🚀 UNIfy API Server Starting...")
    print(f"📍 Server: http://{host}:{port}")
    print("📋 Available Endpoints:")
    print(f"   GET  /                    - Health check")
    print(f"   POST /api/recommendations - Main recommendations endpoint")
    print(f"   GET  /api/test           - Test with sample data")
    print(f"   POST /api/gemini         - Direct Gemini AI endpoint")
    print("\n🔗 Frontend Integration:")
    print(f"   Set your React app to call: http://{host}:{port}/api/recommendations")
    print("\n" + "="*50)

    app.run(host=host, port=port, debug=debug, threaded=True)