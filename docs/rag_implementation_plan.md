# RAG Implementation Plan for Keke.ai Memory System

This document outlines the initial steps required to build the Retrieval-Augmented Generation (RAG) based memory system using the local Markdown files in the `vault/` directory.

## Stage 1: Data Loading & Preparation

*   **Goal:** Read `.md` files, parse YAML frontmatter, extract text, chunk text, and associate metadata with each chunk.
*   **Tasks:**
    1.  **File Discovery:** Implement Python function using `pathlib` or `os.walk` to recursively find all `.md` files within `vault/` subdirectories (`memories`, `knowledge`, `tasks`, `notes`, `relationships`).
    2.  **YAML Parsing:** Use `PyYAML` and potentially `python-frontmatter` to parse the `--- ... ---` block. Handle missing frontmatter gracefully.
    3.  **Text Extraction:** Get the main Markdown content after the frontmatter.
    4.  **Chunking Implementation:**
        *   Use `langchain_text_splitters.RecursiveCharacterTextSplitter`.
        *   Define and tune `chunk_size` (e.g., start ~800) and `chunk_overlap` (e.g., start ~100).
        *   Implement function: `file_content -> list[text_chunks]`.
    5.  **Metadata Association:** For each chunk, create a structured object (e.g., Pydantic model `ChunkWithMetadata`) containing:
        *   `text`: Chunk content.
        *   `source`: Original relative file path.
        *   `chunk_id`: Unique ID within the file.
        *   `metadata`: Parsed YAML frontmatter dictionary.

## Stage 2: Embedding & Storing

*   **Goal:** Generate vector embeddings for each text chunk and store them, along with metadata, in a persistent FAISS index.
*   **Tasks:**
    1.  **Embedding Model Setup:**
        *   Select model (e.g., Google `text-embedding-004`, OpenAI `text-embedding-3-small`, or local Sentence Transformer).
        *   Wrap embedding generation in a function.
    2.  **FAISS Index Initialization:**
        *   Determine embedding dimension.
        *   Initialize `faiss.IndexFlatL2` or `faiss.IndexIVFFlat`.
    3.  **Metadata Storage:** Implement a mapping structure (e.g., Python dictionary `{faiss_index_id: ChunkWithMetadata}`) to link FAISS vector IDs to the corresponding chunk and metadata.
    4.  **Indexing Loop:**
        *   Iterate through all `ChunkWithMetadata` objects.
        *   Generate embedding vector for `chunk.text`.
        *   Add vector to FAISS index, get FAISS ID.
        *   Store `ChunkWithMetadata` in the mapping dict using FAISS ID as key.
    5.  **Persistence:**
        *   Implement save/load functions for the FAISS index (`faiss.write_index`/`faiss.read_index`).
        *   Implement save/load functions for the metadata mapping (e.g., `pickle` or `json`).
    6.  **Update Mechanism (Plan):** Outline strategy for updating the index upon file changes/deletions.

## Stage 3: Retrieval

*   **Goal:** Given a user query, find the most relevant text chunks from the FAISS index.
*   **Tasks:**
    1.  **Load Index & Metadata:** Ensure persistent index and metadata map are loaded.
    2.  **Query Embedding:** Implement function: `user_query_string -> query_vector` (using the same embedding model as Step 2).
    3.  **FAISS Search:**
        *   Use `index.search(query_vector, k)` to get top `k` results (distances and FAISS IDs).
    4.  **Metadata Lookup:** Use returned FAISS IDs to retrieve `ChunkWithMetadata` objects from the mapping.
    5.  **Filtering (Optional):** Implement post-retrieval filtering based on metadata (dates, tags, etc.).
    6.  **Result Formatting:** Implement function: `user_query -> list[relevant_ChunkWithMetadata]`, ready for prompt augmentation. 