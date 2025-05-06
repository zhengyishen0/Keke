# Proof-of-Concept script for Keke.ai RAG pipeline

import os
import faiss
from dotenv import load_dotenv
import google.generativeai as genai
from langchain_text_splitters import RecursiveCharacterTextSplitter
import numpy as np
import yaml
from io import StringIO

# --- Configuration ---
SAMPLE_FILES = ["README.md", "docs/data-structure.md"] # Files to test with
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100
TOP_K_RESULTS = 3 # Number of results to retrieve
TEST_QUERY = "What is the agent architecture?"
EMBEDDING_MODEL_NAME = "models/text-embedding-004" # Google's embedding model
# --- End Configuration ---

def load_and_prep_data(file_paths: list[str]) -> list[dict]:
    """Loads files, extracts text/metadata, and chunks text."""
    chunks_with_metadata = []
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
    )

    for file_path in file_paths:
        print(f"Processing file: {file_path}")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Basic frontmatter parsing attempt (adapt if using python-frontmatter)
            metadata = {}
            text_content = content
            if content.startswith('---'):
                try:
                    end_marker = content.find('---', 3)
                    if end_marker != -1:
                        frontmatter_str = content[3:end_marker]
                        metadata = yaml.safe_load(StringIO(frontmatter_str)) 
                        text_content = content[end_marker+3:].strip()
                except yaml.YAMLError as e:
                    print(f"  Warning: Could not parse YAML frontmatter in {file_path}: {e}")
                except Exception as e:
                     print(f"  Warning: Error processing frontmatter in {file_path}: {e}")

            # Chunk the main content
            chunks = text_splitter.split_text(text_content)
            
            for i, chunk_text in enumerate(chunks):
                chunks_with_metadata.append({
                    "text": chunk_text,
                    "source": file_path,
                    "chunk_id": f"{os.path.basename(file_path)}_chunk_{i}",
                    "metadata": metadata if metadata else {} # Ensure metadata is always a dict
                })
        except FileNotFoundError:
            print(f"  Warning: File not found: {file_path}")
        except Exception as e:
            print(f"  Error processing file {file_path}: {e}")
            
    print(f"Generated {len(chunks_with_metadata)} chunks from {len(file_paths)} files.")
    return chunks_with_metadata

def get_embedding(text: str) -> list[float] | None:
    """Generates embedding for a given text using Google API."""
    try:
        result = genai.embed_content(model=EMBEDDING_MODEL_NAME, content=text)
        return result['embedding']
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return None

def build_in_memory_index(chunks_with_metadata: list[dict]) -> tuple[faiss.Index | None, dict | None]:
    """Builds an in-memory FAISS index and metadata mapping."""
    if not chunks_with_metadata:
        return None, None
        
    print("Generating embeddings for chunks...")
    embeddings = []
    valid_chunks_indices = [] # Keep track of chunks we successfully embedded
    for i, chunk_data in enumerate(chunks_with_metadata):
        embedding = get_embedding(chunk_data["text"])
        if embedding:
            embeddings.append(embedding)
            valid_chunks_indices.append(i)
        else:
            print(f"  Skipping chunk {chunk_data['chunk_id']} due to embedding error.")

    if not embeddings:
        print("Error: No embeddings were generated successfully.")
        return None, None

    embeddings_np = np.array(embeddings).astype('float32')
    dimension = embeddings_np.shape[1]
    print(f"Building FAISS index with dimension {dimension}...")
    
    # Using IndexFlatL2 for simplicity in PoC
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings_np)
    
    print(f"FAISS index built with {index.ntotal} vectors.")
    
    # Create metadata mapping {faiss_id: chunk_data}
    # FAISS IDs are sequential starting from 0 for simple index.add
    metadata_map = {}
    for faiss_id, original_chunk_index in enumerate(valid_chunks_indices):
         metadata_map[faiss_id] = chunks_with_metadata[original_chunk_index]

    return index, metadata_map

def search_index(query: str, index: faiss.Index, metadata_map: dict, k: int) -> list[dict]:
    """Searches the index and returns the top k results with metadata."""
    print(f"\nSearching for query: '{query}'")
    query_embedding = get_embedding(query)
    if not query_embedding:
        print("Error: Could not generate embedding for the query.")
        return []
        
    query_vector = np.array([query_embedding]).astype('float32')
    
    distances, indices = index.search(query_vector, k)
    
    results = []
    print(f"Retrieved {len(indices[0])} results:")
    for i in range(len(indices[0])):
        faiss_id = indices[0][i]
        if faiss_id in metadata_map:
            result_data = metadata_map[faiss_id]
            results.append({
                "faiss_id": int(faiss_id),
                "distance": float(distances[0][i]),
                "source": result_data["source"],
                "chunk_id": result_data["chunk_id"],
                "text": result_data["text"],
                "metadata": result_data["metadata"]
            })
        else:
            print(f"  Warning: Retrieved FAISS ID {faiss_id} not found in metadata map.")
            
    return results

# --- Main Execution --- 
def main():
    load_dotenv() # Load GOOGLE_API_KEY
    if not os.getenv("GOOGLE_API_KEY"):
         print("ERROR: GOOGLE_API_KEY not found. Please set it in your .env file.")
         return

    try:
        genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
    except Exception as e:
        print(f"Error configuring Google AI: {e}")
        return

    # 1. Load and Prepare Data
    all_chunks = load_and_prep_data(SAMPLE_FILES)
    if not all_chunks:
        print("No chunks were generated. Exiting.")
        return

    # 2. Build Index
    index, metadata_map = build_in_memory_index(all_chunks)
    if not index or not metadata_map:
        print("Failed to build index. Exiting.")
        return

    # 3. Search Index
    search_results = search_index(TEST_QUERY, index, metadata_map, TOP_K_RESULTS)
    
    # 4. Print Results (Manual Evaluation)
    print("\n--- Search Results ---")
    if not search_results:
        print("No relevant results found.")
    else:
        for i, res in enumerate(search_results):
            print(f"\nResult {i+1} (Distance: {res['distance']:.4f})")
            print(f"  Source: {res['source']}")
            # print(f"  Metadata: {res['metadata']}") # Optionally print metadata
            # Separate the text printing for clarity and to avoid complex f-string issues
            print(f"  Text: ---------")
            print(res['text'])
            print("----------------")

if __name__ == "__main__":
    main() 