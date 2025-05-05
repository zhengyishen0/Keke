from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.output_parsers import JsonOutputParser
from colorsys import hls_to_rgb
import json
from typing import Dict, List, Any

# Load environment variables from .env file
load_dotenv()

# Emotion analysis chain
emotion_prompt = PromptTemplate(
    input_variables=["input"],
    template="""
    Analyze the emotional tone of this text and represent it as a color in HSL format: {input}
    
    Respond with a JSON object containing:
    - emotion: the primary emotion detected (happy, sad, angry, afraid, calm, excited, love, disgust, surprise, neutral)
    - color: the HSL color representation of this emotion in the format {"hue": float, "saturation": float, "lightness": float}
    
    The HSL values should be:
    - hue: between 0.0 and 1.0 (representing the color wheel)
    - saturation: between 0.0 and 1.0 (representing color intensity)
    - lightness: between 0.0 and 1.0 (representing brightness)
    
    Just return the JSON object without any explanation.
    """
)

def emotion_to_text(emotion_state: Dict[str, float]) -> str:
    hue_desc = {
        (0.0, 0.1): "angry",
        (0.1, 0.2): "excited",
        (0.2, 0.4): "happy",
        (0.4, 0.5): "calm",
        (0.5, 0.7): "sad",
        (0.7, 0.8): "afraid",
        (0.8, 0.9): "surprised",
        (0.9, 1.0): "loving"
    }
    
    emotion_name = "neutral"
    for (low, high), name in hue_desc.items():
        if low <= emotion_state["hue"] < high:
            emotion_name = name
            break
            
    intensity = "mildly" if emotion_state["saturation"] < 0.4 else \
              "moderately" if emotion_state["saturation"] < 0.7 else \
              "intensely"
              
    energy = "with low energy" if emotion_state["lightness"] < 0.4 else \
            "with high energy" if emotion_state["lightness"] > 0.6 else \
            "with moderate energy"
    
    return f"{intensity} {emotion_name} {energy}"

# Subconscious thoughts chain
subconscious_prompt = PromptTemplate(
    input_variables=["input", "emotion", "context"],
    template="""
    A person is feeling {emotion} and they receive this input: "{input}"
    
    Recent context:
    {context}
    
    Generate 3-5 random, associative thoughts that might occur to this person.
    These should be stream-of-consciousness style thoughts colored by their emotional state.
    
    Return just the thoughts as a JSON array of strings without any explanation.
    """
)

# Conscience response chain
conscience_prompt = PromptTemplate(
    input_variables=["input", "emotion", "thoughts", "memories"],
    template="""
    You are responding to this input: "{input}"
    
    Your emotional state: {emotion}
    
    Subconscious thoughts that have arisen:
    {thoughts}
    
    Relevant memories:
    {memories}
    
    Respond naturally as someone with this emotional state, influenced by these thoughts and memories.
    Your response should subtly reflect your emotional state without explicitly mentioning it.
    """
)

class EmotionalAI:
    def __init__(self):
        # Initialize LLMs
        self.emotion_llm = ChatOpenAI(model_name="gpt-4.1-nano", temperature=0.2)
        self.conscience_llm = ChatOpenAI(model_name="gpt-4.1-nano", temperature=0.2)
        self.subconscience_llm = ChatOpenAI(model_name="gpt-4.1-nano", temperature=0.8)
        
        # Initialize RAG memory system
        self.embeddings = OpenAIEmbeddings()
        self.memory = FAISS.from_texts(["Initial memory seed"], self.embeddings)
        
        # Build emotion analysis chain
        self.emotion_chain = (
            emotion_prompt 
            | self.emotion_llm 
            | JsonOutputParser()
            | RunnableLambda(lambda x: x.get("color", {"hue": 0.0, "saturation": 0.0, "lightness": 0.5}))
        )
        
        # Build subconscious chain
        self.subconscious_chain = (
            RunnablePassthrough.assign(
                emotion_text=lambda x: emotion_to_text(x["emotion"]),
                context=lambda x: "\n".join([f"- {item['input']}" for item in x.get("recent_context", [])[-2:]])
            )
            | subconscious_prompt
            | self.subconscience_llm
            | JsonOutputParser()
            | RunnableLambda(lambda x: {"thoughts": x if isinstance(x, list) else [x], "emotion": x["emotion"]})
        )
        
        # Build memory retrieval chain
        self.memory_chain = (
            RunnablePassthrough.assign(
                emotion_text=lambda x: emotion_to_text(x["emotion"]),
                augmented_query=lambda x: f"{x['input']} {x['emotion_text']}"
            )
            | RunnableLambda(lambda x: self.memory.similarity_search(x["augmented_query"], k=3))
            | RunnableLambda(lambda docs: "\n".join([doc.page_content for doc in docs]))
        )
        
        # Build conscience response chain
        self.conscience_chain = (
            RunnablePassthrough.assign(
                emotion_text=lambda x: emotion_to_text(x["emotion"]),
                thoughts_str=lambda x: "\n".join([f"- {thought}" for thought in x["thoughts"]])
            )
            | conscience_prompt
            | self.conscience_llm
        )
        
        # Build main processing chain
        self.main_chain = (
            RunnablePassthrough.assign(
                emotion=lambda x: self.emotion_chain.invoke(x),
                recent_context=lambda x: x.get("recent_context", [])
            )
            | RunnablePassthrough.assign(
                thoughts=lambda x: self.subconscious_chain.invoke(x),
                memories=lambda x: self.memory_chain.invoke(x)
            )
            | self.conscience_chain
        )
    
    def process_input(self, input_text: str, recent_context: List[Dict[str, Any]] = None) -> str:
        """Process an input text and return a response."""
        try:
            # Prepare input data
            input_data = {
                "input": input_text,
                "recent_context": recent_context or []
            }
            
            # Run the chain
            response = self.main_chain.invoke(input_data)
            
            # Update memory with the interaction
            self.memory.add_texts([f"Input: {input_text}\nResponse: {response}"])
            
            return response
        except Exception as e:
            print(f"Error processing input: {e}")
            return "I'm having trouble processing that right now."

def run_test():
    """Run a test interaction with the EmotionalAI."""
    ai = EmotionalAI()
    
    # Test conversation
    test_inputs = [
        "Hello, how are you today?",
        "I'm feeling a bit down because I lost my job.",
        "That's really tough. I'm here to listen if you want to talk about it.",
        "Thank you, that means a lot. I'm just worried about my future.",
        "It's completely normal to feel that way. Would you like to brainstorm some next steps?"
    ]
    
    recent_context = []
    for input_text in test_inputs:
        print(f"\nUser: {input_text}")
        response = ai.process_input(input_text, recent_context)
        print(f"AI: {response}")
        recent_context.append({"input": input_text})

if __name__ == "__main__":
    run_test()