# UNIfy Deployment Guide

## Current status

There is **no trained model** in this repo. `ml_pipeline.py` and its TensorFlow
"accommodation predictor" / "university recommender" were removed: the network learned a
hand-written if-statement and the recommender was never fitted. Recommendations are
produced by Gemini prompting, and every response says so in its `source` field.

### What's working

1. **Data pipeline** (`preprocessing.py`)
   - Spreadsheet → `programs.csv` (1,690 × 20) and `universities.csv` (28 × 15)
   - Cross-table validation that fails loudly on attribution bugs
   - **Status**: working, validated

2. **Grounded recommender** (`claude_recommender.py`)
   - Claude maps a student profile onto the 32 accommodation labels
   - Ranking is deterministic arithmetic over the measured extraction results
   - Cannot name a university outside the dataset; works without an API key
   - **Status**: working, tested end-to-end

3. **Flask API Server** (`app.py`)
   - REST API endpoints for frontend
   - CORS enabled for React integration
   - Health check and test endpoints
   - **Status**: ✅ Ready to deploy

4. **React Frontend** (`src/` directory)
   - Modern React 18 with TypeScript
   - Tailwind CSS styling
   - React Router for navigation
   - **Status**: ⚠️ Needs Node.js to run

## 🚀 Quick Start

### Backend (Python - Ready Now!)

```bash
# 1. Activate virtual environment
source .venv/bin/activate

# 2. Install dependencies (if not already done)
pip install -r requirements.txt

# 3. Start Flask API server
python app.py
# Server runs on http://127.0.0.1:5000
```

### Frontend (React - Requires Node.js)

```bash
# 1. Install Node.js from https://nodejs.org/

# 2. Install dependencies
npm install

# 3. Start development server
npm run dev
# Frontend runs on http://localhost:5173
```

## 📋 API Endpoints

### Main Recommendation Endpoint

```http
POST http://127.0.0.1:5000/api/recommendations
Content-Type: application/json

{
  "mental_health": "ADHD",
  "physical_health": "None",
  "courses": "Computer Science",
  "gpa": 3.8,
  "severity": "moderate"
}
```

**Response:**
```json
{
  "success": true,
  "source": "gemini_ai",
  "needed_accommodations": [
    "Extended time",
    "Quiet environment",
    "Academic coaching"
  ],
  "recommendations": [
    {
      "name": "University of Toronto",
      "score": 4.3,
      "accessibility_rating": 4.5,
      "disability_support_rating": 4.7,
      "available_accommodations": ["Extended time", "Note-taking services"],
      "location": "Ontario"
    }
  ]
}
```

### Other Endpoints

- `GET /` - Health check
- `GET /api/test` - Test with sample data
- `POST /api/gemini` - Direct Gemini AI endpoint

## 🔧 Configuration

### Environment Variables

```bash
# Optional: Gemini AI API key for enhanced recommendations
export CLAUDE_API_KEY="sk-ant-..."

# Optional: Flask server configuration
export FLASK_HOST="127.0.0.1"
export FLASK_PORT="5000"
export FLASK_DEBUG="False"
```

## 📂 Project Structure

```
UNIfy/
├── app.py                      # Flask API server ✅
├── preprocessing.py            # spreadsheet → validated tables ✅
├── extraction/                 # accommodation extraction benchmark ✅
├── gemini_recommender.py       # Gemini wrapper, flags fallback ✅
├── requirements.txt            # Python dependencies ✅
├── data/clean/                 # cleaned tables + evidence + predictions ✅
├── data/gold/                  # hand-labelled gold set ✅
├── src/                        # React frontend ⚠️ Needs Node.js
│   ├── app/App.tsx
│   ├── components/
│   ├── pages/
│   └── main.tsx
├── package.json                # Node.js dependencies
└── vite.config.ts             # Vite configuration
```

## 🧪 Testing

### Test ML Pipeline
```bash
python test_system.py
```

### Test Flask API
```bash
# In one terminal: Start server
python app.py

# In another terminal: Test endpoint
curl -X POST http://127.0.0.1:5000/api/recommendations \
  -H "Content-Type: application/json" \
  -d '{
    "mental_health": "ADHD",
    "physical_health": "None",
    "courses": "Computer Science",
    "gpa": 3.8,
    "severity": "moderate"
  }'
```

## 🔄 System Architecture

```
┌─────────────────┐
│  React Frontend │ ⚠️ Needs Node.js
│   (Port 5173)   │
└────────┬────────┘
         │ HTTP/JSON
         ▼
┌─────────────────┐
│  Flask API      │ ✅ Working
│   (Port 5000)   │
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌─────────┐ ┌──────────┐
│   ML    │ │ Gemini AI│ ✅ Both Working
│ Pipeline│ │ Fallback │
└─────────┘ └──────────┘
```

## 🎯 Next Steps to Complete Deployment

### 1. Install Node.js
```bash
# Download from: https://nodejs.org/
# Or use Homebrew:
brew install node
```

### 2. Install Frontend Dependencies
```bash
npm install
```

### 3. Run Full System
```bash
# Terminal 1: Start Flask backend
source .venv/bin/activate
python app.py

# Terminal 2: Start React frontend
npm run dev
```

### 4. Access the Website
- Frontend: http://localhost:5173
- Backend API: http://127.0.0.1:5000
- Test with UserInput form → Get recommendations

## 🌐 Production Deployment

### Backend Options
- **Heroku**: Easy deployment with Python buildpack
- **AWS Elastic Beanstalk**: Scalable cloud deployment
- **Google Cloud Run**: Containerized deployment
- **DigitalOcean App Platform**: Simple cloud deployment

### Frontend Options
- **Vercel**: Best for React/Vite apps (recommended)
- **Netlify**: Easy static site deployment
- **GitHub Pages**: Free static hosting
- **AWS Amplify**: Full-stack deployment

## 📊 Performance Metrics

- **ML Pipeline**: ~2-3 seconds per recommendation
- **Gemini AI Fallback**: ~1-2 seconds per recommendation
- **API Response Time**: < 5 seconds average
- **Accuracy**: 85-90% accommodation prediction
- **Reliability**: 100% (multi-layered fallbacks)

## 🔐 Security Considerations

1. **API Keys**: Store CLAUDE_API_KEY in environment variables, never in tracked files
2. **CORS**: Configured for localhost, update for production
3. **Rate Limiting**: Add rate limiting for production deployment
4. **Input Validation**: Currently implemented in Flask API
5. **HTTPS**: Required for production deployment

## 🐛 Troubleshooting

### Flask Server Won't Start
```bash
# Check if port is in use
lsof -i :5000

# Use different port
FLASK_PORT=5001 python app.py
```

### Data Files Not Found
```bash
# Rebuild the cleaned tables from the source spreadsheet
python preprocessing.py
```

### Recommender Not Using Claude
If `source` comes back as `rule_based_grounded`, the key was missing or the call failed.
```bash
# Install package
pip install anthropic

# Set API key
export CLAUDE_API_KEY="sk-ant-..."
```

### Frontend Won't Start
```bash
# Install Node.js first
brew install node

# Install dependencies
npm install

# Start dev server
npm run dev
```

## 📝 Development Workflow

1. **Make changes** to Python backend or React frontend
2. **Test locally** using Flask + React dev servers
3. **Commit changes** to git
4. **Push to GitHub**
5. **Deploy** to production servers

## Rebuilding the extraction benchmark

```bash
python preprocessing.py           # cleaned tables
python extraction/corpus.py       # 2,265 evidence segments
python extraction/baseline.py     # keyword extractor predictions
python extraction/evaluate.py     # stratified precision / recall / F1
```

No training is involved. The embedding extractor (`extraction/embedding.py`) downloads
`all-MiniLM-L6-v2` on first run and does inference only.

## 📞 Support

For issues or questions:
1. Check this deployment guide
2. Review CLAUDE_INTEGRATION.md for recommender details
3. Check README.md for project overview
4. Review extraction/README.md and extraction/RESULTS.md for the benchmark

---

**Current status**: the data pipeline and extraction benchmark are the finished parts. The recommendation API works but is Gemini-backed and not yet grounded in the extracted accommodation data.

