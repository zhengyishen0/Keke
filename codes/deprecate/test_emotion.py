from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.output_parsers import JsonOutputParser
from colorsys import hls_to_rgb
import json

# Load environment variables from .env file
load_dotenv()

class EmotionRunnable:
    def __init__(self, llm):
        self.llm = llm
        self.emotion_keywords = {
            "happy": {"hue": 0.3, "saturation": 0.7, "lightness": 0.6},
            "sad": {"hue": 0.6, "saturation": 0.6, "lightness": 0.4},
            "angry": {"hue": 0.05, "saturation": 0.8, "lightness": 0.5},
            "afraid": {"hue": 0.8, "saturation": 0.7, "lightness": 0.3},
            "calm": {"hue": 0.5, "saturation": 0.3, "lightness": 0.5},
            "excited": {"hue": 0.15, "saturation": 0.8, "lightness": 0.6},
            "love": {"hue": 0.9, "saturation": 0.7, "lightness": 0.6},
            "disgust": {"hue": 0.25, "saturation": 0.7, "lightness": 0.4},
            "surprise": {"hue": 0.7, "saturation": 0.8, "lightness": 0.6},
            "neutral": {"hue": 0.0, "saturation": 0.0, "lightness": 0.5}
        }
        
    def _detect_emotion_keywords(self, input_text):
        input_lower = input_text.lower()
        words = input_lower.split()
        detected_emotion = {"hue": 0.0, "saturation": 0.0, "lightness": 0.5}
        highest_saturation = 0
        
        for word in words:
            for emotion, values in self.emotion_keywords.items():
                if emotion in word or word in emotion:
                    if values["saturation"] > highest_saturation:
                        detected_emotion = values.copy()
                        highest_saturation = values["saturation"]
                        
        return detected_emotion, highest_saturation
        
    def _analyze_emotion_llm(self, input_text):
        prompt = PromptTemplate(
            input_variables=["input"],
            template="""
            Analyze the emotional tone of this text: {input}
            
            Respond with a JSON object containing:
            - primary_emotion: the main emotion (happy, sad, angry, afraid, calm, excited, love, disgust, surprise, neutral)
            - intensity: a number from 0.0 to 1.0 indicating how strong the emotion is
            - energy: a number from 0.0 to 1.0 indicating the energy level
            
            Just return the JSON object without explanation.
            """
        )
        
        chain = prompt | self.llm | JsonOutputParser()
        try:
            result = chain.invoke({"input": input_text})
            emotion_name = result.get("primary_emotion", "neutral").lower()
            if emotion_name in self.emotion_keywords:
                detected_emotion = self.emotion_keywords[emotion_name].copy()
                detected_emotion["saturation"] = result.get("intensity", 0.5)
                detected_emotion["lightness"] = result.get("energy", 0.5)
                return detected_emotion
        except:
            pass
        return {"hue": 0.0, "saturation": 0.0, "lightness": 0.5}
        
    def invoke(self, input_text):
        detected_emotion, highest_saturation = self._detect_emotion_keywords(input_text)
        if highest_saturation == 0:
            detected_emotion = self._analyze_emotion_llm(input_text)
        return detected_emotion

class SubconsciousRunnable:
    def __init__(self, llm):
        self.llm = llm
        
    def _emotion_to_text(self, emotion_state):
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
        
    def invoke(self, data):
        input_text = data["input"]
        emotional_state = data["emotion"]
        recent_context = data.get("recent_context", [])
        
        emotion_description = self._emotion_to_text(emotional_state)
        
        context_str = ""
        if recent_context:
            last_items = recent_context[-2:] if len(recent_context) >= 2 else recent_context
            context_str = "\n".join([f"- {item['input']}" for item in last_items])
            
        prompt = PromptTemplate(
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
        
        chain = prompt | self.llm | JsonOutputParser()
        try:
            thoughts = chain.invoke({
                "input": input_text,
                "emotion": emotion_description,
                "context": context_str
            })
            if not isinstance(thoughts, list):
                thoughts = [thoughts]
        except:
            thoughts = ["No thoughts generated"]
            
        return {
            "thoughts": thoughts,
            "emotion": emotional_state
        }

class ConscienceRunnable:
    def __init__(self, llm):
        self.llm = llm
        
    def _emotion_to_text(self, emotion_state):
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
        
    def invoke(self, data):
        input_text = data["input"]
        emotional_state = data["emotion"]
        subconscious_thoughts = data["thoughts"]
        memories = data["memories"]
        
        emotion_text = self._emotion_to_text(emotional_state)
        thoughts_str = "\n".join([f"- {thought}" for thought in subconscious_thoughts])
        
        prompt = PromptTemplate(
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
        
        chain = prompt | self.llm
        response = chain.invoke({
            "input": input_text,
            "emotion": emotion_text,
            "thoughts": thoughts_str,
            "memories": memories
        })
        
        return response

class MemoryRunnable:
    def __init__(self, memory_store):
        self.memory = memory_store
        
    def _emotion_to_text(self, emotion_state):
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
        
    def invoke(self, data):
        input_text = data["input"]
        emotional_state = data["emotion"]
        
        emotion_text = self._emotion_to_text(emotional_state)
        augmented_query = f"{input_text} {emotion_text}"
        
        try:
            results = self.memory.similarity_search(augmented_query, k=3)
            memory_texts = [doc.page_content for doc in results]
            return "\n".join(memory_texts)
        except:
            return "No relevant memories found."

class EmotionalAI:
    def __init__(self):
        # Initialize LLM for conscious processing
        self.conscience_llm = ChatOpenAI(temperature=0.2)
        
        # Initialize smaller LLM for subconscious thoughts
        self.subconscience_llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0.8)
        
        # Initialize RAG memory system
        self.embeddings = OpenAIEmbeddings()
        self.memory = FAISS.from_texts(["Initial memory seed"], self.embeddings)
        
        # Initialize emotional state (HSL)
        self.emotion = {
            "hue": 0.5,  # 0-1 range (color wheel)
            "saturation": 0.5,  # 0-1 range (intensity)
            "lightness": 0.5  # 0-1 range (energy)
        }
        
        # Recent context buffer
        self.recent_context = []
        
        # Initialize runnables
        self.emotion_runnable = EmotionRunnable(self.conscience_llm)
        self.subconscious_runnable = SubconsciousRunnable(self.subconscience_llm)
        self.conscience_runnable = ConscienceRunnable(self.conscience_llm)
        self.memory_runnable = MemoryRunnable(self.memory)
        
        # Create the processing chain
        self.chain = (
            RunnablePassthrough()
            | RunnableLambda(lambda x: {"input": x, "emotion": self.emotion_runnable.invoke(x)})
            | RunnableLambda(lambda x: {**x, "recent_context": self.recent_context})
            | RunnableLambda(lambda x: {**x, **self.subconscious_runnable.invoke(x)})
            | RunnableLambda(lambda x: {**x, "memories": self.memory_runnable.invoke(x)})
            | RunnableLambda(lambda x: self.conscience_runnable.invoke(x))
        )
        
    def process_input(self, input_text):
        """Main processing function for new inputs"""
        # Process through the chain
        response = self.chain.invoke(input_text)
        
        # Get the emotional state from the chain
        emotional_reaction = self.emotion_runnable.invoke(input_text)
        
        # Determine information importance based on emotional intensity
        importance = emotional_reaction["saturation"]
        
        # Store in memory if important enough
        if importance > 0.6:
            self.memory.add_texts([input_text])
            
        # Update recent context
        self.recent_context.append({
            "input": input_text,
            "emotion": emotional_reaction,
            "response": response
        })
        
        if len(self.recent_context) > 5:
            self.recent_context.pop(0)
            
        return response

def run_test():
    ai = EmotionalAI()
    
    test_cases = [
        "Good morning! How are you today?",
        "I'm feeling really frustrated with my project deadline.",
        "I just heard some wonderful news about my friend's promotion!",
        "Can you help me solve this difficult problem?",
        "I'm scared about the upcoming medical procedure."
    ]
    
    print("TESTING EMOTIONAL AI SYSTEM")
    print("===========================\n")
    
    for i, test in enumerate(test_cases):
        print(f"\nTEST CASE {i+1}: '{test}'")
        print("-" * 50)
        
        # Process input
        response = ai.process_input(test)
        
        # Get emotional state
        emotion_text = ai.emotion_runnable.invoke(test)
        
        # Print results
        print(f"Emotional State: {emotion_text}")
        print(f"HSL Values: Hue={ai.emotion['hue']:.2f}, Saturation={ai.emotion['saturation']:.2f}, Lightness={ai.emotion['lightness']:.2f}")
        print("\nResponse:")
        print(response)
        print("\n" + "=" * 50)

if __name__ == "__main__":
    run_test()