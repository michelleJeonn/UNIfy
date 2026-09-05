"""UNUSED -- superseded by claude_recommender.py.

Nothing imports this module. It is kept only for reference and can be deleted.

It is retained mainly as a record of the failure it caused: asked for five Canadian
universities from memory, with a dead API key, it returned UBC, McGill and Alberta --
none of them Ontario schools, none of them in this project's dataset -- reported as a
successful answer. The replacement never lets a model choose the schools.

Gemini AI Fallback Recommender for UNIfy.
Provides AI-powered university accommodation recommendations.
"""

import os
import google.generativeai as genai
from typing import Dict, List, Optional
import json
import warnings
warnings.filterwarnings('ignore')

class GeminiRecommender:
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Gemini AI recommender.
        
        Args:
            api_key: Google AI API key. If None, will try to get from environment variable GEMINI_API_KEY
        """
        # Set whenever a hardcoded default is served, so the caller can report the
        # real source instead of claiming the model answered.
        self.used_fallback = False
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            print("Warning: No Gemini API key provided. Set GEMINI_API_KEY environment variable or pass api_key parameter.")
            self.available = False
            return
        
        try:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-pro')
            self.available = True
            print("Gemini AI recommender initialized successfully!")
        except Exception as e:
            print(f"Failed to initialize Gemini AI: {e}")
            self.available = False
    
    def get_accommodation_recommendations(self, student_profile: Dict) -> List[str]:
        """
        Get accommodation recommendations using Gemini AI.
        
        Args:
            student_profile: Dictionary with student information
            
        Returns:
            List of recommended accommodations
        """
        if not self.available:
            return self._get_default_accommodations(student_profile)
        
        try:
            prompt = self._create_accommodation_prompt(student_profile)
            response = self.model.generate_content(prompt)
            
            # Parse the response to extract accommodations
            accommodations = self._parse_accommodation_response(response.text)
            return accommodations
            
        except Exception as e:
            print(f"Gemini AI accommodation recommendation failed: {e}")
            return self._get_default_accommodations(student_profile)
    
    def get_university_recommendations(self, student_profile: Dict, accommodations: List[str]) -> List[Dict]:
        """
        Get university recommendations using Gemini AI.
        
        Args:
            student_profile: Dictionary with student information
            accommodations: List of needed accommodations
            
        Returns:
            List of university recommendation dictionaries
        """
        if not self.available:
            return self._get_default_universities(student_profile, accommodations)
        
        try:
            prompt = self._create_university_prompt(student_profile, accommodations)
            response = self.model.generate_content(prompt)
            
            # Parse the response to extract university recommendations
            universities = self._parse_university_response(response.text)
            return universities
            
        except Exception as e:
            print(f"Gemini AI university recommendation failed: {e}")
            return self._get_default_universities(student_profile, accommodations)
    
    def _create_accommodation_prompt(self, student_profile: Dict) -> str:
        """Create a prompt for accommodation recommendations."""
        mental_health = student_profile.get('mental_health', 'None')
        physical_health = student_profile.get('physical_health', 'None')
        courses = student_profile.get('courses', 'General')
        gpa = student_profile.get('gpa', 3.0)
        severity = student_profile.get('severity', 'moderate')
        
        prompt = f"""
You are an expert in disability accommodations for university students. Based on the following student profile, recommend appropriate accommodations for university study.

Student Profile:
- Mental Health: {mental_health}
- Physical Health: {physical_health}
- Academic Focus: {courses}
- GPA: {gpa}
- Severity Level: {severity}

Please recommend 3-5 specific accommodations that would be most helpful for this student. Focus on:
1. Academic accommodations (extended time, note-taking, etc.)
2. Environmental accommodations (quiet spaces, accessible facilities, etc.)
3. Support services (counseling, academic coaching, etc.)
4. Technology accommodations (assistive technology, alternative formats, etc.)

Respond with a JSON list of accommodation names only, like this:
["Extended time on exams", "Quiet testing environment", "Note-taking services", "Academic coaching", "Assistive technology access"]

Do not include any other text, just the JSON array.
"""
        return prompt
    
    def _create_university_prompt(self, student_profile: Dict, accommodations: List[str]) -> str:
        """Create a prompt for university recommendations."""
        mental_health = student_profile.get('mental_health', 'None')
        physical_health = student_profile.get('physical_health', 'None')
        courses = student_profile.get('courses', 'General')
        gpa = student_profile.get('gpa', 3.0)
        severity = student_profile.get('severity', 'moderate')
        
        prompt = f"""
You are an expert in university accessibility and disability services. Based on the following student profile and accommodation needs, recommend 5 Canadian universities that would be most suitable.

Student Profile:
- Mental Health: {mental_health}
- Physical Health: {physical_health}
- Academic Focus: {courses}
- GPA: {gpa}
- Severity Level: {severity}
- Needed Accommodations: {', '.join(accommodations)}

Please recommend 5 Canadian universities that have strong disability support services and would be a good match for this student. Consider:
1. Accessibility services quality
2. Available accommodations
3. Disability support staff
4. Campus accessibility
5. Academic reputation in their field

Respond with a JSON array of university objects, like this:
[
  {{
    "name": "University of Toronto",
    "score": 4.5,
    "accessibility_rating": 4.7,
    "disability_support_rating": 4.8,
    "available_accommodations": ["Extended time", "Note-taking services", "Quiet environment"],
    "location": "Ontario",
    "reason": "Excellent disability services and strong academic programs"
  }},
  ...
]

Include exactly 5 universities with realistic scores and detailed accommodation lists. Do not include any other text, just the JSON array.
"""
        return prompt
    
    def _parse_accommodation_response(self, response_text: str) -> List[str]:
        """Parse Gemini response to extract accommodations."""
        try:
            # Clean the response text
            text = response_text.strip()
            if text.startswith('```json'):
                text = text[7:]
            if text.endswith('```'):
                text = text[:-3]
            
            accommodations = json.loads(text)
            if isinstance(accommodations, list):
                return accommodations[:5]  # Limit to 5 accommodations
            else:
                return self._get_default_accommodations({})
                
        except (json.JSONDecodeError, Exception) as e:
            print(f"Failed to parse accommodation response: {e}")
            return self._get_default_accommodations({})
    
    def _parse_university_response(self, response_text: str) -> List[Dict]:
        """Parse Gemini response to extract university recommendations."""
        try:
            # Clean the response text
            text = response_text.strip()
            if text.startswith('```json'):
                text = text[7:]
            if text.endswith('```'):
                text = text[:-3]
            
            universities = json.loads(text)
            if isinstance(universities, list):
                return universities[:5]  # Limit to 5 universities
            else:
                return self._get_default_universities({}, [])
                
        except (json.JSONDecodeError, Exception) as e:
            print(f"Failed to parse university response: {e}")
            return self._get_default_universities({}, [])
    
    def _get_default_accommodations(self, student_profile: Dict) -> List[str]:
        """Get default accommodations when AI is not available."""
        self.used_fallback = True
        mental_health = student_profile.get('mental_health', 'None')
        physical_health = student_profile.get('physical_health', 'None')
        
        accommodations = ['Extended time on exams', 'Academic coaching']
        
        if mental_health != 'None':
            accommodations.extend(['Quiet testing environment', 'Mental health support'])
        
        if physical_health != 'None':
            accommodations.extend(['Accessible facilities', 'Assistive technology'])
        
        return accommodations[:5]
    
    def _get_default_universities(self, student_profile: Dict, accommodations: List[str]) -> List[Dict]:
        """Get default university recommendations when AI is not available.

        NOTE: this list is hardcoded and is not drawn from the project's dataset --
        it names schools outside Ontario that appear nowhere in `universities.csv`.
        It exists so the endpoint returns a shape, not an answer; callers must check
        `source` before showing any of it to a student.
        """
        self.used_fallback = True
        return [
            {
                "name": "University of Toronto",
                "score": 4.3,
                "accessibility_rating": 4.5,
                "disability_support_rating": 4.7,
                "available_accommodations": ["Extended time", "Note-taking services", "Quiet environment", "Academic coaching"],
                "location": "Ontario",
                "reason": "Strong disability services and comprehensive support"
            },
            {
                "name": "University of British Columbia",
                "score": 4.2,
                "accessibility_rating": 4.4,
                "disability_support_rating": 4.6,
                "available_accommodations": ["Extended time", "Assistive technology", "Accessible housing"],
                "location": "British Columbia",
                "reason": "Excellent accessibility infrastructure and support services"
            },
            {
                "name": "McGill University",
                "score": 4.1,
                "accessibility_rating": 4.3,
                "disability_support_rating": 4.5,
                "available_accommodations": ["Extended time", "Academic coaching", "Mental health support"],
                "location": "Quebec",
                "reason": "Comprehensive disability support and academic excellence"
            },
            {
                "name": "University of Alberta",
                "score": 4.0,
                "accessibility_rating": 4.2,
                "disability_support_rating": 4.4,
                "available_accommodations": ["Extended time", "Quiet environment", "Accessible facilities"],
                "location": "Alberta",
                "reason": "Strong disability services and supportive campus environment"
            },
            {
                "name": "University of Waterloo",
                "score": 3.9,
                "accessibility_rating": 4.1,
                "disability_support_rating": 4.3,
                "available_accommodations": ["Extended time", "Assistive technology", "Academic coaching"],
                "location": "Ontario",
                "reason": "Good disability support with strong academic programs"
            }
        ]


def get_gemini_recommendations(student_profile: Dict, api_key: Optional[str] = None) -> Dict:
    """
    Get comprehensive recommendations using Gemini AI as fallback.
    
    Args:
        student_profile: Dictionary with student information
        api_key: Optional Gemini API key
        
    Returns:
        Dictionary with accommodations and university recommendations
    """
    gemini = GeminiRecommender(api_key)
    
    # Get accommodation recommendations
    accommodations = gemini.get_accommodation_recommendations(student_profile)
    
    # Get university recommendations
    universities = gemini.get_university_recommendations(student_profile, accommodations)
    
    return {
        'success': True,
        'source': 'default_fallback' if gemini.used_fallback else 'gemini_ai',
        'needed_accommodations': accommodations,
        'recommendations': universities
    }


if __name__ == "__main__":
    # Test the Gemini recommender
    test_profile = {
        'mental_health': 'ADHD',
        'physical_health': 'None',
        'courses': 'Computer Science',
        'gpa': 3.8,
        'severity': 'moderate'
    }
    
    result = get_gemini_recommendations(test_profile)
    print("Gemini AI Test Results:")
    print(f"Source: {result['source']}")
    print(f"Accommodations: {result['needed_accommodations']}")
    print(f"Universities: {len(result['recommendations'])} recommendations")
    for i, uni in enumerate(result['recommendations'][:3], 1):
        print(f"{i}. {uni['name']} (Score: {uni['score']})")
