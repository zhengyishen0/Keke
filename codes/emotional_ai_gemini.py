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
    exit(1) 

def call_llm(model_name: str = "gemini-2.0-flash",
             system_prompt: str = "", 
             user_prompt: str = "", 
             temperature: float = 0.2, 
             response_format: Dict = {"type": "text"}) -> str:
    """Calls the specified Google Gemini model using the library."""
    try:
        model = genai.GenerativeModel(model_name)
    except Exception as e:
        print(f"Error instantiating model '{model_name}': {e}")
        return f"Error: Could not instantiate model {model_name}"
    
    full_prompt = []
    if system_prompt:
        full_prompt.append(f"{system_prompt}\n\n{user_prompt}")
    else:
        full_prompt.append(user_prompt)

    generation_config = genai.types.GenerationConfig(
        temperature=temperature
    )

    is_json_output = response_format.get("type") == "json_object"
    if is_json_output:
        generation_config.response_mime_type = "application/json"

    try:
        response = model.generate_content(
            full_prompt,
            generation_config=generation_config,
        )
        if response.parts:
            return response.text
        elif response.prompt_feedback.block_reason:
             print(f"API call blocked: {response.prompt_feedback.block_reason}")
             return f"Error: Blocked - {response.prompt_feedback.block_reason}"
        else:
             print(f"Warning: Received empty or unexpected response format: {response}")
             return "Error: Empty response from API"

    except Exception as e:
        print(f"An error occurred during Gemini API call for model '{model_name}': {e}")
        return f"Error: API call failed for {model_name} - {e}"

# System prompts for different components
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
    """

def subconscious_system_prompt(emotion: str) -> str:
    return f"""
    You are a subconscious brain of a human currently feeling {emotion}. Generate 3 random, associative thoughts based on the following input.
    Respond ONLY with a valid JSON object containing a single key "thoughts" which is an array of 3 strings.
    Example Input: "You failed the exam." (assuming emotion is sad)
    Example Output: {{"thoughts": ["Everything feels heavy.", "Why does this always happen?", "I want to hide."]}}
    INPUT:
    """

def conscience_system_prompt(emotion: str, random_thoughts: List[str], chat_history: List[Dict[str, str]] = None) -> str:
    chat_history_str = ""
    if chat_history:
        history_parts = ["\nPrevious conversation context:"] 
        for msg in chat_history:
            role = msg['role'] if msg['role'] in ['user', 'model'] else ('user' if msg['role'] == 'human' else 'model')
            history_parts.append(f"{role}: {msg['content']}")
        chat_history_str = "\n".join(history_parts)
            
    return f"""
    You are the conscience of a human. Your current emotional state is {emotion}.
    Some fleeting thoughts you just had are: {random_thoughts}.
    {chat_history_str}
    Based on your emotion, thoughts, and the conversation history (if any), generate a thoughtful and coherent response to the user's latest input.
    USER'S LATEST INPUT:
    """

def response_with_emotion(input_str: str, chat_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
    # Emotion mind
    emotion_response_raw = call_llm(
        system_prompt=emotion_system_prompt(),
        user_prompt=input_str,
        response_format={"type": "json_object"}
    )
    try:
        emotion_response = json.loads(emotion_response_raw)
    except json.JSONDecodeError:
        print(f"Error decoding JSON from emotion LLM: {emotion_response_raw}")
        emotion_response = {"emotion": "neutral", "color": {"hue": 0.5, "saturation": 0.1, "lightness": 0.5}}
    except TypeError:
        print(f"Error received from emotion LLM call: {emotion_response_raw}")
        emotion_response = {"emotion": "error", "color": {"hue": 0.0, "saturation": 0.0, "lightness": 0.0}}

    # Subconscious mind
    random_thoughts_raw = call_llm(
        system_prompt=subconscious_system_prompt(emotion_response.get('emotion', 'neutral')),
        user_prompt=input_str,
        temperature=emotion_response.get('color', {}).get('saturation', 0.5),
        response_format={"type": "json_object"}
    )
    try:
        random_thoughts = json.loads(random_thoughts_raw)
        if 'thoughts' not in random_thoughts or not isinstance(random_thoughts['thoughts'], list):
             print(f"Unexpected format from subconscious LLM: {random_thoughts_raw}")
             random_thoughts = {"thoughts": ["Default thought 1", "Default thought 2", "Default thought 3"]}
    except json.JSONDecodeError:
        print(f"Error decoding JSON from subconscious LLM: {random_thoughts_raw}")
        random_thoughts = {"thoughts": ["Fallback thought 1", "Fallback thought 2", "Fallback thought 3"]}
    except TypeError:
        print(f"Error received from subconscious LLM call: {random_thoughts_raw}")
        random_thoughts = {"thoughts": ["Error thought 1", "Error thought 2", "Error thought 3"]}

    # Conscience mind
    final_response = call_llm(
        system_prompt=conscience_system_prompt(
            emotion_response.get('emotion', 'neutral'), 
            random_thoughts.get('thoughts', []), 
            chat_history
        ),
        user_prompt=input_str, 
        temperature=emotion_response.get('color', {}).get('lightness', 0.5)
    )

    return {
        "emotion": emotion_response.get('emotion', 'error'),
        "thoughts": random_thoughts.get('thoughts', ['error']),
        "response": final_response
    }

def run_test():
    """Run test using the google-generativeai library call."""
    chat_history = []
    test_inputs = [
        "You are such a good person!",
        "You are terrible!",
        "You failed the most important exam in your life!",
    ]

    for input_text in test_inputs:
        print(f"\nUser: {input_text}")
        if not os.getenv("GOOGLE_API_KEY"):
             print("ERROR: GOOGLE_API_KEY not found.")
             break
        result = response_with_emotion(input_text, chat_history)
        print(f"Emotion: {result['emotion']}")
        print(f"Random Thoughts: {result['thoughts']}")
        print(f"AI Response: {result['response']}")

        chat_history.append({"role": "user", "content": input_text})
        chat_history.append({"role": "model", "content": result['response']})

        if len(chat_history) > 10:
            chat_history = chat_history[-10:]

if __name__ == "__main__":
    run_test()