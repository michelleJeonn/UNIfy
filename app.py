"""
UNIfy Flask API Server
Provides REST API endpoints for the React frontend to access ML/AI recommendations.
"""

from claude_recommender import get_claude_recommendations
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def validate_student_profile(data: dict):
    required_fields = ['mental_health',
                       'physical_health', 'courses', 'gpa', 'severity']
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


# Import our ML/AI systems

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def error_response(message: str, status: int = 400, code: str = "BAD_REQUEST"):
    return jsonify({"success": False, "error": {"code": code, "message": message}}), status


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
            'test': '/api/test',
            'claude': '/api/claude'
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

    Served by claude_recommender.  Claude maps the profile onto the 32 accommodation
    labels in extraction/taxonomy.json; ranking is then deterministic arithmetic over
    the measured extraction results for the 28 Ontario universities in the dataset.
    The model does not choose the schools, so it cannot invent one -- which is exactly
    what the previous Gemini backend did when its key failed.

    `source` is "claude_grounded" when Claude mapped the needs and
    "rule_based_grounded" when it was unavailable and rules did. Both rank only real
    schools; neither fabricates.

    Returns:
    {
        "success": true,
        "source": "claude_grounded|rule_based_grounded",
        "model": "claude-sonnet-5",
        "needed_accommodations": ["Extended time on exams", "Note-taking support"],
        "recommendations": [
            {
                "name": "University of Guelph",
                "score": 3.72,
                "accessibility_rating": 3.6,
                "disability_support_rating": 4.4,
                "rating_basis": "...what the number counts...",
                "matched_accommodations": [...],
                "missing_accommodations": [...],
                "evidence": [{"accommodation": "...", "quote": "..."}],
                "location": "Ontario",
                "reason": "Evidences 6 of 7 needed accommodations..."
            }
        ],
        "grounding": {...extractor and its measured quality...}
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

        logger.info(
            f"Processing recommendation request for: {student_profile}")

        result = get_claude_recommendations(student_profile)

        logger.info(
            f"Recommendation result: success={result['success']}, source={result.get('source', 'unknown')}")

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
        result = get_claude_recommendations(test_profile)

        return jsonify({
            'message': 'Test completed successfully',
            'test_profile': test_profile,
            'result': result
        })

    except Exception as e:
        logger.error(f"Error in test endpoint: {str(e)}")
        return error_response("Internal server error", 500, "INTERNAL_ERROR")


@app.route('/api/claude', methods=['POST'])
@app.route('/api/gemini', methods=['POST'])  # deprecated alias, kept for old clients
def get_claude_recommendations_endpoint():
    """
    Direct recommender endpoint, identical to /api/recommendations.

    /api/gemini is a deprecated alias: the Gemini backend has been replaced. It is
    retained only so existing frontend builds keep working.

    Expected JSON payload: same as /api/recommendations
    """
    try:
        if not request.is_json:
            return error_response("Request must be JSON", 400, "NOT_JSON")

        data = request.get_json()

        # Create student profile (same validation as main endpoint)
        required_fields = ['mental_health',
                           'physical_health', 'courses', 'gpa', 'severity']
        missing_fields = [
            field for field in required_fields if field not in data]

        if missing_fields:
            return error_response(f'Missing required fields: {", ".join(missing_fields)}', 400, "VALIDATION_ERROR")

        student_profile = {
            'mental_health': str(data['mental_health']),
            'physical_health': str(data['physical_health']),
            'courses': str(data['courses']),
            'gpa': float(data['gpa']),
            'severity': str(data['severity'])
        }

        logger.info(f"Processing direct recommender request for: {student_profile}")

        result = get_claude_recommendations(student_profile)

        logger.info(
            f"Recommender result: success={result['success']}, source={result.get('source', 'unknown')}")

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error in direct recommender endpoint: {str(e)}")
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
    print("   GET  /                    - Health check")
    print("   POST /api/recommendations - Main recommendations endpoint")
    print("   GET  /api/test            - Test with sample data")
    print("   POST /api/claude          - Same recommender, direct")
    print("   POST /api/gemini          - Deprecated alias for /api/claude")
    print("\n🔗 Frontend Integration:")
    print(
        f"   Set your React app to call: http://{host}:{port}/api/recommendations")
    print("\n" + "="*50)

    app.run(host=host, port=port, debug=debug, threaded=True)
