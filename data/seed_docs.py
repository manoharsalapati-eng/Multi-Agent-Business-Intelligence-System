import os
import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv

load_dotenv()

CHROMA_PATH = os.getenv("CHROMA_PATH", "chroma_db")

def seed_documents():
    print(f"Initializing ChromaDB persistent store at: {CHROMA_PATH}")
    
    # Initialize Persistent Chroma Client
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    
    # Use sentence-transformers embedding function (free, local)
    # This downloads the "all-MiniLM-L6-v2" model and embeds text locally
    emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    
    # Delete collection if it exists to start fresh
    try:
        client.delete_collection("business_docs")
        print("Removed existing ChromaDB collection.")
    except Exception:
        pass
        
    collection = client.create_collection(
        name="business_docs",
        embedding_function=emb_fn
    )
    
    documents = [
        # Document 1: Return Policy
        "Return Policy:\n"
        "Customers can return any product within 30 days of purchase for a full refund or store exchange. "
        "Standard return shipping is free for all items. Proof of purchase (such as an order confirmation email, receipt, or invoice) is required. "
        "Refund processing takes 5-7 business days after the warehouse receives and inspects the item. "
        "Items must be in original packaging and unused condition. Returns after 30 days are subject to a 15% restocking fee or may be rejected.",
        
        # Document 2: Q2 Sales Report
        "Q2 Sales Report:\n"
        "Sales for the second quarter (Q2) showed robust growth, with a total revenue of $1,240,000, representing a 12% increase quarter-over-quarter. "
        "The North region led all performance metrics, driving 42% of total sales, followed by the West at 35%, and South at 23%. "
        "Widget A remains our top-selling product, contributing $450,000 in revenue. Widget B saw a 15% decline in sales due to supply constraints, which are expected to resolve by early Q3. "
        "Operating expenses were held flat, leading to a net margin expansion of 80 basis points.",
        
        # Document 3: Shipping Guidelines
        "Shipping Guidelines:\n"
        "We offer three shipping options for domestic and international orders. "
        "Standard shipping takes 3-5 business days and is free for orders over $50, otherwise a flat rate of $4.99 applies. "
        "Express shipping takes 1-2 business days and is available for $14.99. Next-Day delivery is available for $29.99 if ordered before 2:00 PM EST. "
        "International shipping delivery times vary by destination, typically taking 7-14 business days, and customs/duties are paid by the customer. "
        "Orders are processed at our central distribution hub within 24 hours of payment authorization.",
        
        # Document 4: Inventory Policy
        "Inventory Policy:\n"
        "Automated replenishment triggers when stock levels fall below their defined reorder point (set per product based on average lead time and daily velocity). "
        "The standard reorder quantity is calculated using the Economic Order Quantity (EOQ) formula. "
        "We aim to maintain a 15% safety stock buffer for high-velocity items, including Widget A and Gadget X. "
        "For slower-moving items like Gizmo Z, the safety stock buffer is reduced to 5%. "
        "In case of stockouts, expedited shipping is authorized for replenishment orders from primary vendors. Inventory audits are conducted bi-annually in June and December."
    ]
    
    ids = [f"doc_{i}" for i in range(len(documents))]
    
    metadatas = [
        {"source": "return_policy.txt", "category": "policy"},
        {"source": "q2_sales_report.txt", "category": "report"},
        {"source": "shipping_guidelines.txt", "category": "shipping"},
        {"source": "inventory_policy.txt", "category": "inventory"}
    ]
    
    collection.add(
        documents=documents,
        ids=ids,
        metadatas=metadatas
    )
    
    print(f"Seeded {len(documents)} document chunks into ChromaDB.")
    
    # Run a quick check
    results = collection.query(
        query_texts=["return policy"],
        n_results=1
    )
    print("Quick retrieval test successful.")
    print(f"Retrieved document ID: {results['ids'][0][0]}")
    print(f"Snippet: {results['documents'][0][0][:100]}...")

if __name__ == "__main__":
    seed_documents()
