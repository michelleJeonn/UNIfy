"""
Gemini AI Recommender for UNIfy
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
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            print("Warning: No Gemini API key provided. Set GEMINI_API_KEY environment variable or pass api_key parameter.")
            self.available = False
            return
        
        try:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-2.5-flash')
            self.available = True
            print("✅ Gemini AI recommender initialized successfully")
        except Exception as e:
            print(f"❌ Failed to initialize Gemini AI: {str(e)}")
            self.available = False

    def get_recommendations(self, student_profile: Dict[str, any]) -> Dict[str, any]:
        """
        Get university recommendations using Gemini AI.
        
        Args:
            student_profile: Dictionary containing student information
            
        Returns:
            Dictionary with recommendations or error information
        """
        if not self.available:
            return {
                "success": False,
                "error": "Gemini AI not available. Please check API key configuration.",
                "source": "gemini_ai"
            }

        try:
            # Create a detailed prompt for Gemini
            prompt = self._create_prompt(student_profile)
            print(f"Generated prompt length: {len(prompt)} characters")
            
            # Get response from Gemini with timeout
            print("Calling Gemini API...")
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=2048,
                    temperature=0.7,
                ),
                safety_settings=[
                    {
                        "category": "HARM_CATEGORY_HARASSMENT",
                        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                    },
                    {
                        "category": "HARM_CATEGORY_HATE_SPEECH",
                        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                    },
                    {
                        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                    },
                    {
                        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                    }
                ]
            )
            print("Received response from Gemini")
            
            # Log raw response details
            print("=" * 50)
            print("RAW GEMINI RESPONSE DEBUG:")
            print("=" * 50)
            print(f"Response object type: {type(response)}")
            print(f"Response candidates: {len(response.candidates) if response.candidates else 0}")
            
            if response.candidates:
                for i, candidate in enumerate(response.candidates):
                    print(f"Candidate {i}:")
                    print(f"  Finish reason: {candidate.finish_reason}")
                    print(f"  Safety ratings: {candidate.safety_ratings}")
                    print(f"  Content parts: {len(candidate.content.parts) if candidate.content and candidate.content.parts else 0}")
                    if candidate.content and candidate.content.parts:
                        for j, part in enumerate(candidate.content.parts):
                            print(f"    Part {j}: {type(part)} - {part.text[:200] if hasattr(part, 'text') and part.text else 'No text'}")
            
            print(f"Response text: {response.text}")
            print(f"Response text length: {len(response.text) if response.text else 0}")
            print("=" * 50)
            
            # Check if response was blocked
            if not response.text:
                print(f"Response blocked. Finish reason: {response.candidates[0].finish_reason if response.candidates else 'Unknown'}")
                fallback = self._create_fallback_response("Response blocked by safety filters")
                return {
                    "success": True,
                    "source": "gemini_ai_fallback",
                    "needed_accommodations": fallback.get("needed_accommodations", []),
                    "recommendations": fallback.get("universities", [])
                }
            
            # Parse the response
            print("Parsing Gemini response...")
            recommendations = self._parse_gemini_response(response.text)
            print(f"Parsed recommendations: {recommendations}")
            
            return {
                "success": True,
                "source": "gemini_ai",
                "needed_accommodations": recommendations.get("needed_accommodations", []),
                "recommendations": recommendations.get("universities", [])
            }
            
        except Exception as e:
            print(f"Error getting Gemini recommendations: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to get recommendations: {str(e)}",
                "source": "gemini_ai"
            }

    def _create_prompt(self, student_profile: Dict[str, any]) -> str:
        """Create a detailed prompt for Gemini AI."""
        return f"""
You are an expert educational counselor specializing in helping students with disabilities find suitable universities. 

Student Profile:
- Mental Health: {student_profile.get('mental_health', 'None')}
- Physical Health: {student_profile.get('physical_health', 'None')}
- Course of Interest: {student_profile.get('courses', 'Not specified')}
- GPA: {student_profile.get('gpa', 'Not specified')}
- Severity Level: {student_profile.get('severity', 'Not specified')}

Please provide university recommendations in the following JSON format:

{{
  "needed_accommodations": ["accommodation1", "accommodation2", "accommodation3"],
  "universities": [
    {{
      "name": "University Name",
      "score": 4.5,
      "accessibility_rating": 4.3,
      "disability_support_rating": 4.7,
      "available_accommodations": ["accommodation1", "accommodation2"],
      "location": "Province/State",
      "reason": "Why this university is suitable for this student"
    }}
  ]
}}

Focus on:
1. Canadian universities with strong disability support services
2. Accommodations that match the student's specific needs
3. Universities known for the student's field of study
4. Accessibility ratings and support quality
5. Practical reasons why each university would be suitable

Provide 3-5 university recommendations with detailed explanations.
"""

    def _parse_gemini_response(self, response_text: str) -> Dict[str, any]:
        """Parse Gemini's response and extract structured data."""
        print(f"Parsing response text (length: {len(response_text)}):")
        print(f"First 500 chars: {response_text[:500]}")
        print(f"Last 500 chars: {response_text[-500:]}")
        
        try:
            # Try to find JSON in the response
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            print(f"JSON start index: {start_idx}, end index: {end_idx}")
            
            if start_idx != -1 and end_idx != -1:
                json_str = response_text[start_idx:end_idx]
                print(f"Extracted JSON string (length: {len(json_str)}):")
                print(f"JSON: {json_str}")
                
                parsed_json = json.loads(json_str)
                print(f"Successfully parsed JSON: {parsed_json}")
                return parsed_json
            else:
                print("No JSON found in response, using fallback")
                # Fallback: create structured response from text
                return self._create_fallback_response(response_text)
                
        except json.JSONDecodeError as e:
            print(f"JSON parsing failed: {str(e)}")
            print(f"Failed JSON string: {json_str if 'json_str' in locals() else 'N/A'}")
            # If JSON parsing fails, create a fallback response
            return self._create_fallback_response(response_text)

    def _create_fallback_response(self, response_text: str) -> Dict[str, any]:
        """Create a fallback response when JSON parsing fails."""
        return {
            "needed_accommodations": [
                "Extended time for exams",
                "Note-taking services",
                "Academic coaching",
                "Priority registration"
            ],
            "universities": [
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
        }


# Global instance
_gemini_recommender = None

def get_gemini_recommendations(student_profile: Dict[str, any]) -> Dict[str, any]:
    """
    Get recommendations from Gemini AI.
    
    Args:
        student_profile: Dictionary containing student information
        
    Returns:
        Dictionary with recommendations or error information
    """
    global _gemini_recommender
    
    if _gemini_recommender is None:
        _gemini_recommender = GeminiRecommender()
    
    return _gemini_recommender.get_recommendations(student_profile)


def get_university_roadmap_details(university_name: str, student_profile: Dict[str, any]) -> Dict[str, any]:
    """
    Get detailed roadmap information for a specific university using Gemini AI.
    
    Args:
        university_name: Name of the university
        student_profile: Dictionary containing student information
        
    Returns:
        Dictionary with roadmap details (documents, eligibility, financial aid)
    """
    global _gemini_recommender
    
    if _gemini_recommender is None or not _gemini_recommender.available:
        return {
            "success": False,
            "error": "Gemini AI not available",
            "source": "gemini_ai"
        }
    
    try:
        # Create a detailed prompt for university-specific roadmap
        prompt = f"""
You are an expert educational counselor specializing in helping students with disabilities navigate university admissions.

Student Profile:
- Mental Health: {student_profile.get('mental_health', 'None')}
- Physical Health: {student_profile.get('physical_health', 'None')}
- Course of Interest: {student_profile.get('courses', 'Not specified')}
- GPA: {student_profile.get('gpa', 'Not specified')}
- Severity Level: {student_profile.get('severity', 'Not specified')}

Provide detailed roadmap information for {university_name} in the following JSON format:

{{
  "required_documents": {{
    "general": ["document1", "document2"],
    "disability_specific": ["document1", "document2"],
    "notes": "Additional notes about documentation requirements"
  }},
  "eligibility": {{
    "gpa_requirement": "Minimum GPA required",
    "prerequisites": ["prerequisite1", "prerequisite2"],
    "disability_accommodations": ["accommodation1", "accommodation2"],
    "notes": "Additional eligibility information"
  }},
  "financial_aid": {{
    "available_aids": ["aid1", "aid2"],
    "disability_grants": ["grant1", "grant2"],
    "application_process": "How to apply for financial aid",
    "notes": "Additional financial aid information"
  }}
}}

Focus on:
1. Specific requirements for students with {student_profile.get('mental_health', 'disabilities')} and/or {student_profile.get('physical_health', 'disabilities')}
2. Disability accommodation documentation requirements
3. Available financial aid for students with disabilities
4. Step-by-step guidance for the application process

Provide detailed, specific information about {university_name} including links to disability services and financial aid offices when relevant.
"""
        
        print(f"Calling Gemini AI for roadmap details for {university_name}...")
        response = _gemini_recommender.model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=2048,
                temperature=0.7,
            ),
            safety_settings=[
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                }
            ]
        )
        
        if not response.text:
            return {
                "success": False,
                "error": "Response blocked by safety filters",
                "source": "gemini_ai"
            }
        
        # Parse the response
        roadmap_details = _gemini_recommender._parse_gemini_response(response.text)
        
        return {
            "success": True,
            "source": "gemini_ai",
            "university_name": university_name,
            "roadmap": roadmap_details
        }
        
    except Exception as e:
        print(f"Error getting roadmap details: {str(e)}")
        return {
            "success": False,
            "error": f"Failed to get roadmap details: {str(e)}",
            "source": "gemini_ai"
        }
