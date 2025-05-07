import json
import os
from dotenv import load_dotenv
from typing import Dict, List, Any
import litellm

# Load environment variables
load_dotenv()

# API Key will be picked up by LiteLLM from GOOGLE_API_KEY or GEMINI_API_KEY
if not os.getenv("GOOGLE_API_KEY") and not os.getenv("GEMINI_API_KEY"):
    print("ERROR: GOOGLE_API_KEY or GEMINI_API_KEY environment variable not set.")
    exit(1)

# Set LiteLLM verbosity for debugging if needed
# litellm.set_verbose = True

def call_llm(model_name: str, # Model name will be like "gemini/model-identifier"
             system_prompt: str = "", 
             user_prompt: str = "", 
             temperature: float = 0.2, 
             response_format: Dict = {"type": "text"}) -> str:
    """Calls the specified model via LiteLLM."""
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})
    
    extra_kwargs = {}
    is_json_output = response_format.get("type") == "json_object"
    if is_json_output:
        extra_kwargs["response_format"] = {"type": "json_object"}
        # Ensure the prompt also guides the model to produce JSON

    try:
        # print(f"Calling LiteLLM with model: {model_name}, messages: {messages}, temp: {temperature}, kwargs: {extra_kwargs}") # Debug print
        response = litellm.completion(
            model=model_name,
            messages=messages,
            temperature=temperature,
            **extra_kwargs
        )
        # Accessing the content from LiteLLM response
        content = response.choices[0].message.content
        if content:
            return content
        else:
            # Handle cases where content might be None (e.g. safety blocked, though LiteLLM might raise specific exceptions)
            print(f"Warning: Received None content from LiteLLM. Full response: {response}")
            # Check for block reasons if available in the response structure
            # This part might need adjustment based on how LiteLLM surfaces block reasons for Gemini
            if hasattr(response, 'prompt_filter_results') and response.prompt_filter_results:
                 print(f"API call potentially blocked by content filter: {response.prompt_filter_results}")
                 return f"Error: Blocked by content filter - {response.prompt_filter_results}"
            return "Error: Empty content from API"

    except litellm.exceptions.APIError as e: # Catch specific LiteLLM API errors
        print(f"LiteLLM APIError for model '{model_name}': {e}")
        return f"Error: API call failed for {model_name} - {e}"
    except Exception as e:
        print(f"An unexpected error occurred during LiteLLM call for model '{model_name}': {e}")
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

def response_with_emotion(input_str: str, chat_history: List[Dict[str, str]] = None, 
                          model_id_for_llm: str = "gemini/gemini-1.5-flash-latest") -> Dict[str, Any]:
    
    current_model_to_test = model_id_for_llm
    print(f"--- Using model: {current_model_to_test} ---")

    # Emotion mind
    emotion_response_raw = call_llm(
        model_name=current_model_to_test,
        system_prompt=emotion_system_prompt(),
        user_prompt=input_str,
        response_format={"type": "json_object"}
    )
    try:
        emotion_response = json.loads(emotion_response_raw)
    except (json.JSONDecodeError, TypeError): 
        print(f"Error decoding/handling JSON from emotion LLM: {emotion_response_raw}")
        emotion_response = {"emotion": "error_parsing_emotion", "color": {"hue": 0.0, "saturation": 0.0, "lightness": 0.0}}

    # Subconscious mind
    random_thoughts_raw = call_llm(
        model_name=current_model_to_test,
        system_prompt=subconscious_system_prompt(emotion_response.get('emotion', 'neutral')),
        user_prompt=input_str,
        temperature=emotion_response.get('color', {}).get('saturation', 0.5),
        response_format={"type": "json_object"}
    )
    try:
        random_thoughts = json.loads(random_thoughts_raw)
        if 'thoughts' not in random_thoughts or not isinstance(random_thoughts['thoughts'], list):
             print(f"Unexpected format from subconscious LLM: {random_thoughts_raw}")
             random_thoughts = {"thoughts": ["Default thought 1 (parsing error)", "Default thought 2", "Default thought 3"]}
    except (json.JSONDecodeError, TypeError):
        print(f"Error decoding/handling JSON from subconscious LLM: {random_thoughts_raw}")
        random_thoughts = {"thoughts": ["Fallback thought 1 (parsing error)", "Fallback thought 2", "Fallback thought 3"]}

    # Conscience mind
    final_response = call_llm(
        model_name=current_model_to_test,
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

# --- run_test to try different models with LiteLLM --- 
def run_test():
    """Run test using LiteLLM with different model identifiers."""
    
    # Models to test with LiteLLM. LiteLLM uses gemini/ for Google AI Studio
    # Attempting gemini/gemini-2.0-flash as requested.
    models_to_try = [
        "gemini/gemini-2.0-flash" 
    ]

    chat_history = []
    test_inputs = [
        "You are such a good person!",
        "You are terrible!",
        "You failed the most important exam in your life!",
    ]

    if not os.getenv("GOOGLE_API_KEY") and not os.getenv("GEMINI_API_KEY"):
        print("ERROR: GOOGLE_API_KEY or GEMINI_API_KEY not found.")
        return

    for model_to_test in models_to_try:
        print(f"\n==================== TESTING MODEL: {model_to_test} ====================")
        chat_history = [] # Reset history for each model test
        for input_text in test_inputs:
            print(f"\nUser: {input_text}")
            result = response_with_emotion(input_text, chat_history, model_id_for_llm=model_to_test)
            print(f"Emotion: {result['emotion']}")
            print(f"Random Thoughts: {result['thoughts']}")
            print(f"AI Response: {result['response']}")

            chat_history.append({"role": "user", "content": input_text})
            # LiteLLM usually returns role 'assistant' from completion, but we map to 'model' for Gemini history
            chat_history.append({"role": "model", "content": result['response']}) 

            if len(chat_history) > 10:
                chat_history = chat_history[-10:]

if __name__ == "__main__":
    run_test()