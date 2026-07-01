import json
import chromadb
from chromadb.utils import embedding_functions
from bs4 import BeautifulSoup
from typing import List, Dict

# Configuration
JSON_FILE = "crawl_results.json"
CHROMA_PERSIST_DIR = "./chroma_db"
COLLECTION_NAME = "win32_docs"
CHUNK_SIZE = 5000 # Characters per chunk
CHUNK_OVERLAP = 50 # Characters overlap to maintain context

def load_and_parse_json(file_path: str) -> List[Dict]:
    """Loads the JSON file and extracts clean text from HTML snippets."""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    documents = []
    metadatas = []
    ids = []

    print(f"Processing {len(data)} items...")
    
    for i, item in enumerate(data):
        html_content = item.get("snippet", "")
        url = item.get("url", "")
        title = item.get("title", "")
        
        # Parse HTML with BeautifulSoup
        soup = BeautifulSoup(html_content, "html.parser")
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "header", "footer"]):
            script.decompose()
        
        # Get text and clean whitespace
        text = soup.get_text(separator=" ", strip=True)
        
        # Skip if text is too short (likely empty or just noise)
        if len(text) < 50:
            continue
            
        documents.append(text)
        metadatas.append({
            "url": url,
            "title": title,
            "depth": item.get("depth", 0),
            "source": "win32_crawl"
        })
        # Create a unique ID based on index and URL hash
        ids.append(f"doc_{i}_{abs(hash(url)) % 10000}")

    return documents, metadatas, ids

def chunk_text(documents: List[str], metadatas: List[Dict], ids: List[str]) -> tuple:
    """
    Splits large documents into smaller overlapping chunks.
    Returns expanded lists of chunks, metadata, and IDs.
    """
    all_chunks = []
    all_metadatas = []
    all_ids = []
    
    print("Chunking documents...")
    
    for i, doc in enumerate(documents):
        # Simple sliding window chunking
        start = 0
        doc_len = len(doc)
        chunk_count = 0
        
        while start < doc_len:
            end = start + CHUNK_SIZE
            chunk = doc[start:end]
            
            # Only add if chunk is substantial
            if len(chunk.strip()) > 20:
                all_chunks.append(chunk)
                # Add chunk index to metadata for tracing
                meta = metadatas[i].copy()
                meta["chunk_index"] = chunk_count
                all_metadatas.append(meta)
                all_ids.append(f"{ids[i]}_chunk_{chunk_count}")
                chunk_count += 1
            
            start += (CHUNK_SIZE - CHUNK_OVERLAP)
            
    return all_chunks, all_metadatas, all_ids

def build_vector_store(documents, metadatas, ids):
    """Initializes ChromaDB and adds the processed documents."""
    
    # Initialize Persistent Client (saves to disk)
    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    
    # Use Sentence Transformers for local embeddings (free, no API key needed)
    # You can change model_name to "all-MiniLM-L6-v2" for a faster, smaller model
    embedding_func = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    
    # Get or create collection
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_func,
        metadata={"hnsw:space": "cosine"} # Cosine similarity is standard for text
    )
    
    # Check if collection already has data to avoid duplicates on re-run
    if collection.count() == 0:
        print(f"Adding {len(documents)} chunks to vector store...")
        
        # ChromaDB handles batching internally, but for very large datasets 
        # you might want to batch manually (e.g., 1000 at a time)
        collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        print("Ingestion complete.")
    else:
        print(f"Collection already contains {collection.count()} documents. Skipping ingestion.")
        
    return collection

def query_rag(collection, query_text: str, n_results: int = 3):
    """Queries the vector store and returns relevant context."""
    print(f"\n--- Query: '{query_text}' ---")
    
    results = collection.query(
        query_texts=[query_text],
        n_results=n_results,
        include=["documents", "metadatas", "distances"]
    )
    
    if not results['documents'][0]:
        return "No relevant documents found."
    
    output = []
    for i, doc in enumerate(results['documents'][0]):
        meta = results['metadatas'][0][i]
        dist = results['distances'][0][i]
        
        output.append(f"""
        [Result {i+1}] (Distance: {dist:.4f})
        Source: {meta['url']}
        Title: {meta['title']}
        Content: {doc[:]}
        """)
        
    return "\n".join(output)

if __name__ == "__main__":
    # 1. Load and Parse
    docs, metas, ids = load_and_parse_json(JSON_FILE)
    
    if not docs:
        print("No valid documents found to process.")
        exit()

    # 2. Chunk
    chunks, chunk_metas, chunk_ids = chunk_text(docs, metas, ids)
    
    # 3. Build Store
    collection = build_vector_store(chunks, chunk_metas, chunk_ids)
    
    # 4. Query Example
    # Replace with a question relevant to your Win32 API data
    user_query = "How do I create a window in Win32?"
    response = query_rag(collection, user_query)
    print(response)   