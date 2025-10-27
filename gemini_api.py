from google import genai
from google.genai import types
import certifi
print(certifi.where())

# API_TOKEN: AIzaSyDA4fcpDdFF2_JVGaKhO9u4Y64phOqWc6U


# 1. Initialize the client
# The client automatically picks up the API key from the environment variable.
try:
    client = genai.Client()
except Exception as e:
    print(f"Error initializing client. Make sure GEMINI_API_KEY is set. Error: {e}")
    exit()

# 2. Define a System Instruction (Optional but powerful)
# This gives the model a persona and rules for the entire interaction.
system_instruction = (
    "You are a friendly, enthusiastic, and brief travel itinerary planner. "
    "Your response must be formatted as a short list of 3 bullet points."
)

# 3. Define the User's Prompt
user_prompt = "Plan a fun, 3-day weekend trip to Rome, Italy for a foodie."

# 4. Configure the generation
# This is where you pass in the system instruction and other settings.
config = types.GenerateContentConfig(
    system_instruction=system_instruction,
    temperature=0.8,  # A bit of randomness for a creative itinerary
)

# 5. Make the API Call
print("Sending request to Gemini...")
try:
    response = client.models.generate_content(
        model="gemini-2.5-flash",  # Use a fast, capable model
        contents=user_prompt,
        config=config,
    )

    # 6. Print the result
    print("\n--- Gemini's Itinerary ---")
    print(response.text)
    print("--------------------------\n")

except Exception as e:
    print(f"An error occurred during content generation: {e}")