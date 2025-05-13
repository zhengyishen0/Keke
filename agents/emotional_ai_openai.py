import json
from typing import Dict, List, Any
from openai import OpenAI
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI()

def call_llm(model_name: str = "gpt-4.1-nano", system_prompt: str = "", user_prompt: str = "", temperature: float = 0.2, response_format: Dict = {"type": "text"}) -> Dict[str, Any]:
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=temperature,
        response_format=response_format
    )
    return response.choices[0].message.content

# System prompts for different components
def emotion_system_prompt() -> str:
    return """
    You are the emotional brain of a human. Generate a emotion reaction based on the given information and represent it as a color in HSL format.

    Respond with a JSON object containing:
    - emotion: the primary emotion detected (happy, sad, angry, afraid, calm, excited, love, disgust, surprise, neutral)
    - color: the HSL color representation of this emotion in the format {"hue": float, "saturation": float, "lightness": float}

    The HSL values should be:
    - hue: between 0.0 and 1.0 (representing the color wheel), which should represent the mood in color hue.
    - saturation: between 0.0 and 1.0 (representing color intensity), which should represent the intensity of the mood.
    - lightness: between 0.0 and 1.0 (representing brightness), which should represent the energy level of the mood.
    """

def subconscious_system_prompt(emotion: str) -> str:
    return f"""
    You are a subconscious brain of a human. Generate random, associative thoughts that might occur 
    to you in the tone and mood of {emotion}.
    Return the thoughts as a JSON array of strings.
    """

def conscience_system_prompt(emotion: str, random_thoughts: List[str], chat_history: List[Dict[str, str]] = None) -> str:
    chat_history_str = ""
    if chat_history:
        chat_history_str = "\nPrevious conversation:\n"
        for msg in chat_history:
            chat_history_str += f"{msg['role']}: {msg['content']}\n"
    
    return f"""
    You are the conscience of a human. Generate a reaction to the given situation that is in the tone and mood of {emotion} and based on the random thoughts: {random_thoughts}.
    
    {chat_history_str}
    
    Consider the conversation history when formulating your response to maintain context and continuity.
    """

def response_with_emotion(input: str, chat_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
    # The emotion mind
    emotion_response = json.loads(call_llm(
        system_prompt=emotion_system_prompt(),
        user_prompt=input,
        response_format={"type": "json_object"}
    ))
    
    # The subconscious mind
    random_thoughts = json.loads(call_llm(
        system_prompt=subconscious_system_prompt(emotion_response['emotion']),
        user_prompt=f"You are having the mood of {emotion_response['emotion']}. What are the first 3 internal thoughts that come to mind when you receive this input: {input}",
        temperature=emotion_response['color']['saturation'],
        response_format={"type": "json_object"}
    ))
    
    # The conscience mind
    final_response = call_llm(
        system_prompt=conscience_system_prompt(emotion_response['emotion'], random_thoughts, chat_history),
        user_prompt=f"Please respond to this input: {input} given that your first 3 internal thoughts are: {random_thoughts}",
        temperature=emotion_response['color']['lightness']
    )
    
    return {
        "emotion": emotion_response['emotion'],
        "thoughts": random_thoughts['thoughts'],
        "response": final_response
    }

def run_test():
    """Run a test interaction with the EmotionalAI."""
    # Test conversation with chat history
    chat_history = []
    test_inputs = [
        "You are such a good person!",
        "You are a son of bitch!",
        "You failed in the most important exam in your life!",
    ]
    
    for input_text in test_inputs:
        print(f"\nUser: {input_text}")
        result = response_with_emotion(input_text, chat_history)
        print(f"Emotion: {result['emotion']}")
        print(f"Random Thoughts: {result['thoughts']}")
        print(f"AI Response: {result['response']}")
        
        # Update chat history
        chat_history.append({"role": "user", "content": input_text})
        chat_history.append({"role": "assistant", "content": result['response']})
        
        # Keep only the last 5 exchanges to maintain context
        if len(chat_history) > 10:  # 5 exchanges (user + assistant)
            chat_history = chat_history[-10:]

if __name__ == "__main__":
    run_test()