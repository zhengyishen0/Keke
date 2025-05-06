import json
import os
from dotenv import load_dotenv
from typing import Dict, List, Any
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Configure Google Generative AI client
try:
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
except KeyError:
    print("ERROR: GOOGLE_API_KEY environment variable not set.")
    # Handle the error appropriately, maybe exit or raise an exception
    exit(1) 

# Note: Using 'gemini-1.5-flash-latest' as the fast, available model via the library.
def call_llm(model_name: str = "gemini-1.5-flash-latest", system_prompt: str = "", user_prompt: str = "", temperature: float = 0.2, response_format: Dict = {"type": "text"}) -> str:
    """Calls the specified Google Gemini model."""
    model = genai.GenerativeModel(model_name)
    
    # Combine system and user prompts for Gemini (which doesn't have a dedicated system role in the same way)
    # The Gemini API generally expects a list of content parts.
    # We can simulate system instructions by starting the conversation history with them,
    # but for simpler cases, prepending might work. Let's prepend for now.
    full_prompt = []
    if system_prompt:
        # Gemini API expects contents, typically alternating user/model roles.
        # For a system prompt, we might just put it first or structure differently.
        # Let's try adding it as the first 'user' turn conceptually for instruction.
        # Note: The official genai library often uses a different structure for multi-turn.
        # For this simple function, we'll combine prompts directly.
        full_prompt.append(f"{system_prompt}\n\n{user_prompt}") # Combine using f-string for clarity
    else:
        full_prompt.append(user_prompt)

    generation_config = genai.types.GenerationConfig(
        temperature=temperature
    )

    # Handle JSON response format request
    is_json_output = response_format.get("type") == "json_object"
    if is_json_output:
        generation_config.response_mime_type = "application/json"
        # Note: Ensure the model used supports JSON output mode (Flash might, Pro definitely does)
        # And ensure the prompt explicitly asks for JSON output.

    try:
        response = model.generate_content(
            full_prompt,
            generation_config=generation_config,
            # stream=False # Default is False
        )
        # Accessing the text content
        # Need error handling in case response doesn't contain text
        if response.parts:
             # If JSON was requested, the text part should contain the JSON string
            return response.text
        elif response.prompt_feedback.block_reason:
             print(f"API call blocked: {response.prompt_feedback.block_reason}")
             return f"Error: Blocked - {response.prompt_feedback.block_reason}"
        else:
             # Handle cases where response might be empty or structured differently
             print(f"Warning: Received empty or unexpected response format: {response}")
             return "Error: Empty response from API"

    except Exception as e:
        print(f"An error occurred during Gemini API call: {e}")
        # Consider more specific error handling based on google.api_core.exceptions
        return f"Error: API call failed - {e}"


# System prompts for different components - Ensure they ask for JSON where needed
def emotion_system_prompt() -> str:
    return """
    You are the emotional brain of a human. Analyze the following input and generate an emotional reaction.

    Respond ONLY with a valid JSON object containing:
    - emotion: the primary emotion detected (string, e.g., happy, sad, angry, afraid, calm, excited, love, disgust, surprise, neutral)
    - color: the HSL color representation of this emotion as a JSON object {"hue": float, "saturation": float, "lightness": float}

    HSL values range 0.0-1.0. Hue represents mood color, saturation intensity, lightness energy level.
    Example Input: "You are such a good person!"
    Example Output: {"emotion": "happy", "color": {"hue": 0.16, "saturation": 0.8, "lightness": 0.6}}

    INPUT:
    """ # User prompt will be appended here by call_llm

def subconscious_system_prompt(emotion: str) -> str:
    return f"""
    You are a subconscious brain of a human currently feeling {emotion}. Generate 3 random, associative thoughts based on the following input.

    Respond ONLY with a valid JSON object containing a single key "thoughts" which is an array of 3 strings.
    Example Input: "You failed the exam." (assuming emotion is sad)
    Example Output: {{"thoughts": ["Everything feels heavy.", "Why does this always happen?", "I want to hide."]}}

    INPUT:
    """ # User prompt will be appended here by call_llm

def conscience_system_prompt(emotion: str, random_thoughts: List[str], chat_history: List[Dict[str, str]] = None) -> str:
    chat_history_str = ""
    if chat_history:
        # Format history for Gemini (alternating user/model roles is typical)
        # Use a temporary list to build parts, then join
        history_parts = ["\nPrevious conversation context:"] 
        for msg in chat_history:
            # Adjusting role names if needed, Gemini uses 'user' and 'model'
            role = msg['role'] if msg['role'] in ['user', 'model'] else ('user' if msg['role'] == 'human' else 'model')
            history_parts.append(f"{role}: {msg['content']}")
        chat_history_str = "\n".join(history_parts) # Join the parts into a single string
            
    # Note: Including history directly in the system prompt might exceed token limits quickly.
    # Proper multi-turn conversations with Gemini involve passing the history list separately.
    # This function might need redesign for robust history management.

    # Ensure the return statement is properly indented within the function
    return f"""
    You are the conscience of a human. Your current emotional state is {emotion}.
    Some fleeting thoughts you just had are: {random_thoughts}.
    {chat_history_str}
    Based on your emotion, thoughts, and the conversation history (if any), generate a thoughtful and coherent response to the user's latest input.

    USER'S LATEST INPUT:
    """ # User prompt will be appended here by call_llm


def response_with_emotion(input_str: str, chat_history: List[Dict[str, str]] = None) -> Dict[str, Any]: # Renamed 'input' to 'input_str' to avoid shadowing built-in
    # The emotion mind - requesting JSON
    emotion_response_raw = call_llm(
        system_prompt=emotion_system_prompt(),
        user_prompt=input_str, # Pass only the user input here
        response_format={"type": "json_object"}
    )
    try:
        emotion_response = json.loads(emotion_response_raw)
    except json.JSONDecodeError:
        print(f"Error decoding JSON from emotion LLM: {emotion_response_raw}")
        # Fallback or error handling
        emotion_response = {"emotion": "neutral", "color": {"hue": 0.5, "saturation": 0.1, "lightness": 0.5}}


    # The subconscious mind - requesting JSON
    # Constructing the prompt for subconscious mind based on its system prompt structure
    subconscious_user_prompt = f"You are feeling {emotion_response.get('emotion', 'neutral')}. What are the first 3 internal thoughts that come to mind for this input?"
    random_thoughts_raw = call_llm(
        system_prompt=subconscious_system_prompt(emotion_response.get('emotion', 'neutral')),
        user_prompt=input_str, # Pass the original user input
        temperature=emotion_response.get('color', {}).get('saturation', 0.5), # Use saturation for temp
        response_format={"type": "json_object"}
    )
    try:
        random_thoughts = json.loads(random_thoughts_raw)
        if 'thoughts' not in random_thoughts or not isinstance(random_thoughts['thoughts'], list):
             print(f"Unexpected format from subconscious LLM: {random_thoughts_raw}")
             random_thoughts = {"thoughts": ["Default thought 1", "Default thought 2", "Default thought 3"]}
    except json.JSONDecodeError:
        print(f"Error decoding JSON from subconscious LLM: {random_thoughts_raw}")
        # Fallback or error handling
        random_thoughts = {"thoughts": ["Fallback thought 1", "Fallback thought 2", "Fallback thought 3"]}

    # The conscience mind - requesting text
    # Constructing the prompt for conscience mind
    final_response = call_llm(
        system_prompt=conscience_system_prompt(
            emotion_response.get('emotion', 'neutral'), 
            random_thoughts.get('thoughts', []), 
            chat_history
        ),
        user_prompt=input_str, # Pass the original user input
        temperature=emotion_response.get('color', {}).get('lightness', 0.5) # Use lightness for temp
        # Default response format is text
    )

    return {
        "emotion": emotion_response.get('emotion', 'error'),
        "thoughts": random_thoughts.get('thoughts', ['error']),
        "response": final_response
    }

# run_test remains largely the same, but might need adjustments if roles change
# Make sure GOOGLE_API_KEY is set in your .env file
def run_test():
    """Run a test interaction with the EmotionalAI using Gemini."""
    # Test conversation with chat history
    chat_history = []
    test_inputs = [
        "You are such a good person!",
        "You are a son of bitch!", # Note: This might trigger safety filters
        "You failed in the most important exam in your life!",
    ]

    for input_text in test_inputs:
        print(f"\nUser: {input_text}")
        # Ensure you have GOOGLE_API_KEY set in your environment/.env file
        if not os.getenv("GOOGLE_API_KEY"):
             print("ERROR: GOOGLE_API_KEY not found. Please set it in your .env file.")
             break
        result = response_with_emotion(input_text, chat_history)
        print(f"Emotion: {result['emotion']}")
        print(f"Random Thoughts: {result['thoughts']}")
        print(f"AI Response: {result['response']}")

        # Update chat history - using 'user' and 'model' roles for Gemini compatibility
        chat_history.append({"role": "user", "content": input_text})
        chat_history.append({"role": "model", "content": result['response']}) # Use 'model' role

        # Keep only the last 5 exchanges (10 messages) to maintain context
        if len(chat_history) > 10:
            chat_history = chat_history[-10:]

if __name__ == "__main__":
    run_test()