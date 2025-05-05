from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from colorsys import hls_to_rgb
import json

# Load environment variables from .env file
load_dotenv()

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
        
    def process_input(self, input_text):
        """Main processing function for new inputs"""
        # Step 1: Process through emotion layer first
        emotional_reaction = self._process_emotion_layer(input_text)
        
        # Step 2: Determine information importance based on emotional intensity
        importance = emotional_reaction["saturation"]
        
        # Step 3: Store in memory if important enough
        if importance > 0.6:
            self.memory.add_texts([input_text])
        
        # Step 4: Process through subconscious with emotional coloring
        subconscious_response = self._process_subconscious_layer(input_text, emotional_reaction)
        subconscious_thoughts = subconscious_response["thoughts"]
        
        # Step 5: Retrieve relevant memories based on input and emotion
        relevant_memories = self._retrieve_relevant_memories(input_text, emotional_reaction)
        
        # Step 6: Process through conscious mind
        response = self._process_conscience_layer(
            input_text,
            emotional_reaction,
            subconscious_thoughts,
            relevant_memories
        )
        
        # Step 7: Update recent context for future processing
        self.recent_context.append({
            "input": input_text,
            "emotion": emotional_reaction,
            "thoughts": subconscious_thoughts,
            "response": response
        })
        
        if len(self.recent_context) > 5:
            self.recent_context.pop(0)
            
        return response
        
    def _process_emotion_layer(self, input_text):
        """First layer: Process input through emotion system"""
        # Analyze input text for emotional content
        # This would ideally use a sophisticated sentiment analysis model
        # For simplicity, we'll use keyword mapping
        
        emotion_keywords = {
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
        
        # Simple preprocessing - lowercase and tokenization
        input_lower = input_text.lower()
        words = input_lower.split()
        
        # Default to neutral emotion
        detected_emotion = {"hue": 0.0, "saturation": 0.0, "lightness": 0.5}
        
        # Check for emotional keywords
        highest_saturation = 0
        for word in words:
            for emotion, values in emotion_keywords.items():
                if emotion in word or word in emotion:
                    # Take the emotion with highest saturation (intensity)
                    if values["saturation"] > highest_saturation:
                        detected_emotion = values.copy()
                        highest_saturation = values["saturation"]
                        
        # If no emotion detected through keywords, use LLM for more sophisticated analysis
        if highest_saturation == 0:
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
            
            chain = LLMChain(llm=self.conscience_llm, prompt=prompt)
            result_text = chain.run(input=input_text)
            
            try:
                result = json.loads(result_text)
                emotion_name = result.get("primary_emotion", "neutral").lower()
                if emotion_name in emotion_keywords:
                    detected_emotion = emotion_keywords[emotion_name].copy()
                    detected_emotion["saturation"] = result.get("intensity", 0.5)
                    detected_emotion["lightness"] = result.get("energy", 0.5)
            except:
                # Keep default emotion if parsing fails
                pass
                
        # Apply smoothing with previous emotional state for continuity
        self.emotion["hue"] = (self.emotion["hue"] * 0.3) + (detected_emotion["hue"] * 0.7)
        self.emotion["saturation"] = (self.emotion["saturation"] * 0.3) + (detected_emotion["saturation"] * 0.7)
        self.emotion["lightness"] = (self.emotion["lightness"] * 0.3) + (detected_emotion["lightness"] * 0.7)
        
        return self.emotion.copy()
        
    def _process_subconscious_layer(self, input_text, emotional_state):
        """Second layer: Generate thoughts colored by emotional state"""
        # Convert emotional state to words for prompting
        emotion_rgb = hls_to_rgb(emotional_state["hue"], 
                               emotional_state["lightness"], 
                               emotional_state["saturation"])
        
        emotion_description = self._emotion_to_text(emotional_state)
        
        # Include recent context for associative thinking
        context_str = ""
        if self.recent_context:
            last_items = self.recent_context[-2:] if len(self.recent_context) >= 2 else self.recent_context
            context_str = "\n".join([f"- {item['input']}" for item in last_items])
        
        # Prompt for random thoughts
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
        
        chain = LLMChain(llm=self.subconscience_llm, prompt=prompt)
        result_text = chain.run(
            input=input_text,
            emotion=emotion_description,
            context=context_str
        )
        
        # Extract thoughts from result
        try:
            thoughts = json.loads(result_text)
            if not isinstance(thoughts, list):
                thoughts = [result_text]
        except:
            # Fallback if JSON parsing fails
            thoughts = [result_text]
            
        return {
            "thoughts": thoughts,
            "emotion": emotional_state
        }
    
    def _process_conscience_layer(self, input_text, emotional_state, subconscious_thoughts, memories):
        """Third layer: Conscious processing integrating all elements"""
        # Convert emotion to text description
        emotion_text = self._emotion_to_text(emotional_state)
        
        # Format subconscious thoughts
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
        
        chain = LLMChain(llm=self.conscience_llm, prompt=prompt)
        response = chain.run(
            input=input_text,
            emotion=emotion_text,
            thoughts=thoughts_str,
            memories=memories
        )
        
        return response
    
    def _retrieve_relevant_memories(self, input_text, emotional_state):
        """Retrieve memories relevant to current input and emotional state"""
        # Create a combined query with input and emotional state
        emotion_text = self._emotion_to_text(emotional_state)
        augmented_query = f"{input_text} {emotion_text}"
        
        # Retrieve from memory
        try:
            results = self.memory.similarity_search(augmented_query, k=3)
            memory_texts = [doc.page_content for doc in results]
            return "\n".join(memory_texts)
        except:
            return "No relevant memories found."
    
    def _emotion_to_text(self, emotion_state):
        """Convert emotional state to text description"""
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
        
        # Find matching emotion
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
        emotion_text = ai._emotion_to_text(ai.emotion)
        
        # Print results
        print(f"Emotional State: {emotion_text}")
        print(f"HSL Values: Hue={ai.emotion['hue']:.2f}, Saturation={ai.emotion['saturation']:.2f}, Lightness={ai.emotion['lightness']:.2f}")
        print("\nResponse:")
        print(response)
        print("\n" + "=" * 50)

if __name__ == "__main__":
    run_test()