# UNIfy - University Accommodation Recommendation System

UNIfy is an intelligent recommendation system that helps students with disabilities find universities that best match their accessibility needs and accommodation requirements. The project combines a machine learning backend with a modern React frontend.

## 🎯 Project Overview

The system uses machine learning to:
- **Predict accommodations** needed based on student disability profiles
- **Recommend universities** that provide the best match for accessibility needs
- **Match students** with institutions based on accommodation availability and support ratings

## 🚀 Quick Start

### Prerequisites

- **Node.js** (latest version) - [Download here](https://nodejs.org/en/download/)
- **Python 3.8+** (for ML backend)
- **AWS Account** (for authentication and database)
- **AWS CLI** configured with credentials
- **8GB+ RAM** (for TensorFlow training)

### Frontend Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/michelleJeonn/UNIfy.git
   cd UNIfy
   ```

2. **Install frontend dependencies**
   ```bash
   npm install
   ```

3. **Configure AWS credentials**
   ```bash   
   aws configure
   # When prompted, enter:
   # - AWS Access Key ID
   # - AWS Secret Access Key
   # - Default region name: us-east-2
   # - Default output format: json
   ```


4. **Start Amplify sandbox (in a separate terminal)**
   ```bash
   npx ampx sandbox
   ```
   Keep this running during development. This creates:
   AWS Cognito User Pool (authentication)
   DynamoDB tables (user profiles and recommendation history)
   **sandbox is running if it shows "Watching for file changes..."**


5. **Create a test user**
   Get your User Pool ID from the sandbox output, then run:
   ```bash
   # Replace us-east-2_XXXXXXXXX with your actual User Pool ID
   aws cognito-idp admin-create-user \
     --user-pool-id us-east-2_XXXXXXXXX \
     --username test@example.com \
     --user-attributes Name=email,Value=test@example.com Name=email_verified,Value=true \
     --message-action SUPPRESS \
     --region us-east-2

   aws cognito-idp admin-set-user-password \
     --user-pool-id us-east-2_XXXXXXXXX \
     --username test@example.com \
     --password TestPassword123! \
     --permanent \
     --region us-east-2
   ```

6. **Run the frontend locally**
   ```bash
   npm run dev
   ```


### Backend Setup (ML Pipeline)

1. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Verify TensorFlow installation**
   ```bash
   python -c "import tensorflow as tf; print(f'TensorFlow {tf.__version__} installed successfully')"
   ```

3. **Train the ML models**
   ```bash
   python ml_pipeline.py
   ```

## 📊 Data Structure

### Cleaned CSV Files

Your cleaned CSV files contain valuable information for building the ML model:

1. **`clean_student_info.csv`** - Student disability profiles and course information
   - Mental health conditions (ADHD, Autism, Depression, etc.)
   - Physical health conditions (Hearing, Mobility, Neurological, etc.)
   - High school courses completed

2. **`clean_uni_info.csv`** - University information and available accommodations
   - University names and locations
   - Available accommodations and services
   - Accessibility and disability support ratings

3. **`clean_user_input.csv`** - Student input data for training
   - GPA and academic performance
   - Health condition details
   - Severity levels and preferences

## 🤖 Machine Learning Pipeline

### 1. Train the Models

Run the complete ML pipeline to train the recommendation system:

```bash
python ml_pipeline.py
```

This will:
- Load and preprocess your cleaned CSV data
- Create training datasets from student and university information
- Train a neural network to predict needed accommodations
- Build a university recommendation system
- Save trained models to the `models/` directory

### 2. Model Architecture

#### Accommodation Predictor
- **Input**: Student disability profile, courses, GPA, severity
- **Output**: Predicted accommodations needed
- **Architecture**: 4-layer neural network with dropout regularization
- **Training**: Binary cross-entropy loss for multi-label classification

#### University Recommender
- **Input**: University features and accommodation availability
- **Output**: Match scores for student-university pairs
- **Scoring**: Combines accessibility ratings (70%) with accommodation match (30%)

### 3. Data Processing

The pipeline automatically:
- Encodes categorical variables (disabilities, courses, accommodations)
- Scales numerical features (GPA, ratings)
- Handles missing data and data inconsistencies
- Creates synthetic training data when needed

## 🔌 Frontend Integration API

### 1. Main API Function

The system provides a simple API function for frontend integration:

```python
from ml_pipeline import get_recommendations

# Student profile input
student_profile = {
    'mental_health': 'ADHD',
    'physical_health': 'None',
    'courses': 'Computer Science',
    'gpa': 3.8,
    'severity': 'moderate'
}

# Get recommendations
result = get_recommendations(student_profile)

if result['success']:
    accommodations = result['needed_accommodations']
    universities = result['recommendations']
    print(f"Recommended accommodations: {accommodations}")
    print(f"Top universities: {universities}")
```

### 2. Input Format

The `student_profile` dictionary should contain:

- **`mental_health`**: str - Mental health condition (e.g., 'ADHD', 'Autism', 'Depression', 'None')
- **`physical_health`**: str - Physical health condition (e.g., 'Hearing', 'Mobility', 'Neurological', 'None')
- **`courses`**: str - High school courses (e.g., 'Computer Science', 'Mathematics', 'Arts')
- **`gpa`**: float - Grade point average (0.0 to 4.0)
- **`severity`**: str - Condition severity ('mild', 'moderate', 'severe')

### 3. Output Format

The function returns a dictionary with:

```python
{
    'success': True,
    'needed_accommodations': ['Extended time', 'Quiet environment', 'Academic coaching'],
    'recommendations': [
        {
            'name': 'University of Toronto',
            'score': 4.2,
            'accessibility_rating': 4.5,
            'disability_support_rating': 4.8,
            'available_accommodations': ['Extended time', 'Quiet environment', ...],
            'location': 'Ontario'
        },
        # ... more universities
    ]
}
```

### 4. Error Handling

If the function fails, it returns:

```python
{
    'success': False,
    'error': 'Error message describing what went wrong',
    'recommendations': []
}
```

## 📈 Model Performance

### Training Metrics
- **Accommodation Predictor**: Accuracy typically 85-90%
- **University Recommender**: Mean Absolute Error < 0.3
- **Training Time**: ~5-10 minutes on standard hardware

### Evaluation
The system evaluates:
- Accommodation prediction accuracy
- University recommendation relevance
- Match score distribution
- User satisfaction metrics

## 🔧 Customization

### Adding New Disabilities
1. Update the disability options in your frontend
2. Retrain the model with new data
3. Update the encoding mappings

### Adding New Universities
1. Add university data to `clean_uni_info.csv`
2. Include accommodation information
3. Add accessibility ratings

### Modifying Accommodations
1. Update accommodation lists in the ML pipeline
2. Retrain models with new accommodation categories
3. Update your frontend options

## 📁 Project Structure

```
UNIfy/
├── data/
│   └── clean/                 # Cleaned CSV files
│       ├── clean_student_info.csv
│       ├── clean_uni_info.csv
│       └── clean_user_input.csv
├── models/                    # Trained ML models (created after training)
│   ├── accommodation_predictor.h5
│   ├── university_recommender.h5
│   └── encoders.pkl
├── src/                       # React frontend
│   ├── components/
│   ├── pages/
│   └── app/
├── html-pages/               # Legacy HTML pages
├── public/                   # Static assets
├── ml_pipeline.py           # ML training pipeline and API functions
├── test_system.py           # System testing and demonstration
├── requirements.txt         # Python dependencies
├── package.json             # Node.js dependencies
└── README.md                # This file
```

## 🚨 Troubleshooting

### Common Issues

1. **Memory Errors During Training**
   - Reduce batch size in `ml_pipeline.py`
   - Use smaller neural network architectures
   - Process data in chunks

2. **Model Loading Errors**
   - Ensure models are trained first (`python ml_pipeline.py`)
   - Check file paths in the API function
   - Verify TensorFlow version compatibility

3. **Data Loading Issues**
   - Check CSV file paths and permissions
   - Verify CSV format and encoding
   - Handle missing or corrupted data

4. **Frontend Issues**
   - Ensure Node.js is installed and up to date
   - Clear npm cache: `npm cache clean --force`
   - Delete `node_modules` and reinstall: `rm -rf node_modules && npm install`

### Performance Optimization

1. **Faster Training**
   - Use GPU acceleration if available
   - Reduce training epochs
   - Use smaller datasets for testing

2. **Faster Inference**
   - Load models once at startup
   - Cache frequently used data
   - Optimize feature encoding

### Amplify Issues

1. **"amplify_outputs.json not found"**
   ```bash
   # Make sure sandbox is running
   npx ampx sandbox
   ```
2. **"Already signed in user"**
   ```bash
   # Clear browser storage or use incognito mode
   # Session persistence is normal behavior
   ```
3. **"Can't find variable: signInUser"
   ```bash
   # Restart dev server
   # Press Ctrl+C then run:
   npm run dev

   # Verify auth service exists
   ls -la src/services/auth.ts
   ```


## 🔮 Future Enhancements

### Planned Features
- **Real-time Updates**: Live accommodation availability
- **Student Reviews**: Peer feedback on accessibility
- **Advanced Analytics**: Detailed accessibility insights
- **Full Frontend Integration**: Complete React UI with ML backend

### Model Improvements
- **Deep Learning**: Transformer-based architectures
- **Multi-modal**: Text and image analysis
- **Personalization**: User preference learning
- **A/B Testing**: Continuous model optimization

## 📚 Technical Details

### Frontend Stack
- **React 18**: Modern UI framework
- **TypeScript**: Type-safe JavaScript
- **Vite**: Fast build tool and dev server
- **Tailwind CSS**: Utility-first CSS framework

### Machine Learning Stack
- **TensorFlow 2.x**: Neural network training and inference
- **scikit-learn**: Data preprocessing and evaluation
- **pandas**: Data manipulation and analysis
- **numpy**: Numerical computations

### API Design
- **Simple Function Interface**: Easy to integrate with any frontend
- **JSON-like Output**: Standardized response format
- **Error Handling**: Graceful failure with informative messages
- **Model Management**: Automatic model loading and training

## 🤝 Frontend Integration Guide

### For React/JavaScript Developers

```javascript
// Example API call from frontend
const getRecommendations = async (studentProfile) => {
    try {
        const response = await fetch('/api/recommendations', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(studentProfile)
        });
        
        const result = await response.json();
        return result;
    } catch (error) {
        console.error('Error getting recommendations:', error);
        return { success: false, error: error.message };
    }
};
```

### For Python Backend Developers

```python
# Direct import and usage
from ml_pipeline import get_recommendations

@app.route('/api/recommendations', methods=['POST'])
def api_recommendations():
    student_profile = request.json
    result = get_recommendations(student_profile)
    return jsonify(result)
```

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📞 Support

For questions or support:
- Create an issue in the repository
- Contact the development team
- Check the troubleshooting section above

---

**UNIfy** - Empowering students with disabilities to find their perfect university match through intelligent technology and comprehensive accessibility information.
