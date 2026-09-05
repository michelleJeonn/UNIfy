# UNIfy - Gemini API & Flask Integration Guide

## Overview

UNIfy integrates Google's Gemini AI with a Flask backend to provide personalized university recommendations for students with disabilities. The system uses both machine learning models and Gemini AI as a fallback to ensure reliable recommendations.

## Architecture

```
React Frontend (Port 5173)
    ↓ HTTP Requests
Flask API Server (Port 5000)
    ↓ Calls
ML Pipeline → Gemini AI (Fallback)
```

## Features

- **Intelligent Fallback System**: Uses ML models first, falls back to Gemini AI if needed
- **RESTful API**: Clean Flask API with proper error handling
- **Real-time Recommendations**: Instant university and accommodation suggestions
- **Responsive UI**: Modern React interface with loading states and error handling

## Quick Start

### 1. Environment Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Install Node dependencies
npm install
```

### 2. Configuration

Create a `.env` file:
```bash
# Flask Configuration
FLASK_HOST=127.0.0.1
FLASK_PORT=5000
FLASK_DEBUG=True
FRONTEND_ORIGINS=http://localhost:5173,http://localhost:3000

# Gemini AI Configuration
CLAUDE_API_KEY=sk-ant-your-key-here

# React Configuration
VITE_API_URL=http://localhost:5000
```

### 3. Start Development Servers

**Option A: Use the startup script**
```bash
./start-dev.sh
```

**Option B: Manual startup**
```bash
# Terminal 1 - Flask Backend
source .venv/bin/activate
python app.py

# Terminal 2 - React Frontend
npm run dev
```

### 4. Test the Integration

**Option A: Use the test script**
```bash
python test_integration.py
```

**Option B: Manual testing**
- Visit: http://localhost:5173
- Fill out the user input form
- View personalized recommendations

## API Endpoints

### Main Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check |
| POST | `/api/recommendations` | Get university recommendations |
| GET | `/api/test` | Test with sample data |
| POST | `/api/gemini` | Direct Gemini AI endpoint |

### Sample Request

```bash
curl -X POST http://localhost:5000/api/recommendations \
  -H "Content-Type: application/json" \
  -d '{
    "mental_health": "ADHD",
    "physical_health": "None",
    "courses": "Computer Science",
    "gpa": 3.8,
    "severity": "moderate"
  }'
```

### Sample Response

```json
{
  "success": true,
  "source": "gemini_ai",
  "needed_accommodations": [
    "Extended time on exams",
    "Quiet testing environment",
    "Note-taking services"
  ],
  "recommendations": [
    {
      "name": "University of Toronto",
      "score": 4.5,
      "accessibility_rating": 4.7,
      "disability_support_rating": 4.8,
      "available_accommodations": ["Extended time", "Academic coaching"],
      "location": "Ontario",
      "reason": "Excellent disability support services"
    }
  ]
}
```

## React Frontend Integration

### API Service (`src/services/api.ts`)

```typescript
import { getRecommendations } from '../services/api';

const profile = {
  mental_health: 'ADHD',
  physical_health: 'None',
  courses: 'Computer Science',
  gpa: 3.8,
  severity: 'moderate'
};

const result = await getRecommendations(profile);
```

### User Flow

1. **User Input** (`/information`) - Collect student profile data
2. **API Call** - Send profile to Flask backend
3. **Processing** - ML pipeline processes with Gemini fallback
4. **Results** (`/recommendations`) - Display personalized recommendations

## Error Handling

The system includes comprehensive error handling:

- **Network errors**: Connection issues with API
- **Validation errors**: Invalid input data
- **AI service errors**: Gemini API failures with fallbacks
- **Loading states**: User feedback during processing

## Troubleshooting

### Common Issues

**Flask server won't start:**
```bash
# Check if port 5000 is in use
lsof -i :5000

# Try a different port
export FLASK_PORT=5001
```

**Gemini API errors:**
```bash
# Verify API key is set
echo $CLAUDE_API_KEY

# Check API quota and permissions
```

**CORS issues:**
```bash
# Verify FRONTEND_ORIGINS in .env
FRONTEND_ORIGINS=http://localhost:5173,http://localhost:3000
```

### Debug Mode

Enable debug logging:
```bash
export FLASK_DEBUG=True
python app.py
```

## Development

### Project Structure

```
UNIfy/
├── app.py                 # Flask API server
├── claude_recommender.py  # grounded recommender (Claude + dataset)
├── preprocessing.py       # spreadsheet → validated tables
├── extraction/            # accommodation extraction benchmark
├── test_integration.py    # Integration tests
├── start-dev.sh          # Development startup script
├── src/
│   ├── services/api.ts   # API service layer
│   ├── pages/
│   │   ├── UserInput.tsx # Form component
│   │   └── Recommendations.tsx # Results display
│   └── ...
└── requirements.txt      # Python dependencies
```

### Adding New Features

1. **Backend**: Add endpoints to `app.py`
2. **AI Integration**: Extend `gemini_recommender.py`
3. **Frontend**: Update API service and components
4. **Testing**: Add tests to `test_integration.py`

## Deployment

### Production Considerations

- Use proper environment variables
- Enable HTTPS for API calls
- Set up proper CORS policies
- Use production WSGI server (gunicorn)
- Implement rate limiting
- Add API authentication

### Environment Variables

```bash
# Production Flask
FLASK_ENV=production
FLASK_DEBUG=False
FLASK_HOST=0.0.0.0

# Secure Gemini API key management
CLAUDE_API_KEY=sk-ant-your-production-key
```

## Support

For issues or questions:
1. Check the troubleshooting section
2. Run `python test_integration.py` to verify setup
3. Check Flask and React logs for errors
4. Verify environment variables are set correctly

---

*This integration provides a robust foundation for AI-powered university recommendations with proper error handling and user experience considerations.*
