"""UNUSED -- superseded by claude_recommender.py at the repo root.

Nothing imports this module; the Flask API does not use it. Kept for reference only.
Note that _initialize_client calls exit() on failure, which would terminate the host
process -- another reason not to wire this in as-is.
"""

from google import genai
from google.genai import types
import certifi

class GeminiAPI:
    def __init__(self, api_key=None):
        self.api_key = api_key
        self.client = None
        self.system_instruction = (
            "You are a friendly and enthusiastic college consultant who advises students who might potentially be mentally or physically impaired on university selections."
            "Please answer in a json format, feel free to be as verbose as possible, we should not be succinct just because the response is in a data structured format."
        )
        self._initialize_client()

    def _initialize_client(self):
        try:
            self.client = genai.Client()
        except Exception as e:
            print(f"Error initializing client. Make sure GEMINI_API_KEY is set. Error: {e}")
            exit()

    @staticmethod
    def generate_prompt(profile):
        mental_health = profile.get("mental_health", "unknown")
        physical_health = profile.get("physical_health", "unknown")
        courses = profile.get("courses", [])
        gpa = profile.get("gpa", 0.0)
        severity = profile.get("severity", "unknown")

        prompt_template = (
            f"Suppose I am a 17 year old who has {severity} symptoms of {mental_health} and {physical_health} and want to study {courses} with a high school gpa of {gpa} in Canada."
            f"Can you give me 3 university recommendations with justified medical reasons for why these programs would be suitable for my condition?"
            f"If possible, calculate a score out of 10 on appropriate fit."
        )
        return prompt_template

    def generate_recommendations(self, profile):
        user_prompt = self.generate_prompt(profile)
        config = types.GenerateContentConfig(
            system_instruction=self.system_instruction,
            temperature=0.8,  # A bit of randomness for a creative itinerary
        )

        print("Sending request to Gemini...")
        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",  # Use a fast, capable model
                contents=user_prompt,
                config=config,
            )

            print("\n--- Gemini's Recommendations ---")
            print(response.text)
            print("--------------------------\n")
            return response.text

        except Exception as e:
            print(f"An error occurred during content generation: {e}")
            return None


# Example usage:
if __name__ == "__main__":
    print(certifi.where())  # Debugging SSL certificates

    profile = {
        "mental_health": "anxiety",
        "physical_health": "asthma",
        "courses": ["computer science", "mathematics"],
        "gpa": 3.8,
        "severity": "moderate",
    }

    gemini_api = GeminiAPI()
    gemini_api.generate_recommendations(profile)
