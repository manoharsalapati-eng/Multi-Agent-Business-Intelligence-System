import os
from typing import Dict, Any, List
import chromadb
from chromadb.utils import embedding_functions
from utils.llm_client import llm_client
from dotenv import load_dotenv

load_dotenv()

CHROMA_PATH = os.getenv("CHROMA_PATH", "chroma_db")

def query_vector_store(query: str, n_results: int = 5) -> List[Dict[str, Any]]:
    """
    Connects to ChromaDB, runs embedding similarity query, and returns documents with source metadata.
    """
    if not os.path.exists(CHROMA_PATH):
        print(f"ChromaDB store path not found: {CHROMA_PATH}. Ensure seed_docs.py was run.")
        return []
        
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    
    try:
        collection = client.get_collection(
            name="business_docs",
            embedding_function=emb_fn
        )
        
        results = collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        chunks = []
        if results and "documents" in results and results["documents"]:
            docs = results["documents"][0]
            metadatas = results["metadatas"][0] if "metadatas" in results and results["metadatas"] else [{}] * len(docs)
            ids = results["ids"][0] if "ids" in results and results["ids"] else [""] * len(docs)
            
            for doc, meta, doc_id in zip(docs, metadatas, ids):
                chunks.append({
                    "id": doc_id,
                    "content": doc,
                    "source": meta.get("source", "unknown"),
                    "category": meta.get("category", "unknown")
                })
        return chunks
    except Exception as e:
        print(f"ChromaDB retrieval error: {e}")
        return []

def run_rag_agent(query: str) -> Dict[str, Any]:
    """
    RAG Agent Flow: Retrieve document chunks -> Format Context ->
    Prompt LLM under strict grounding constraints -> Return output.
    """
    # Retrieve top 5 documents
    chunks = query_vector_store(query, n_results=5)
    
    if not chunks:
        return {
            "query": query,
            "retrieved_chunks": [],
            "explanation": "No relevant documents could be found in the knowledge base."
        }
        
    # Format retrieved chunks as context string
    context_list = []
    for chunk in chunks:
        context_list.append(f"Source: {chunk['source']}\nContent: {chunk['content']}")
    context_str = "\n\n---\n\n".join(context_list)
    
    system_prompt = f"""Answer the question using ONLY the context below. If the context doesn't
contain the answer, say so clearly — do not make up information.

Context:
{context_str}
"""
    
    try:
        explanation = llm_client.query(
            prompt=f"Question: {query}",
            system_prompt=system_prompt
        )
        
        return {
            "query": query,
            "retrieved_chunks": chunks,
            "explanation": explanation
        }
    except Exception as e:
        print(f"RAG Agent LLM error: {e}")
        return {
            "query": query,
            "retrieved_chunks": chunks,
            "explanation": f"RAG Agent was unable to summarize the retrieved documents. Error: {str(e)}"
        }

if __name__ == "__main__":
    # Test RAG Agent
    print("Testing RAG Agent...")
    test_result = run_rag_agent("What is the return policy?")
    print("Retrieved Chunks Count:", len(test_result["retrieved_chunks"]))
    print("Explanation:\n", test_result["explanation"])
