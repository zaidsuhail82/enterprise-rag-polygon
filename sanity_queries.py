from src.retrieval.bm25_retriever import BM25Retriever
from src.retrieval.vector_store import VectorStore
from src.ingestion.embedder import Embedder

# Initialize your components
bm25 = BM25Retriever()
vs = VectorStore()
embedder = Embedder()

# Define the queries here
test_queries = [
    "technical compliance requirements Shamadhan",
    "Shamadhan digital wallet commercial proposal",
    "market deployment status Polygon Panamax"
]

for q in test_queries:
    print(f"\n--- Testing Query: {q} ---")
    
    # 1. BM25 Search
    bm25_res = bm25.search(q, top_k=1)
    if bm25_res:
        print(f"BM25 Top Match: {bm25_res[0]['payload'].get('name', 'N/A')}")
    else:
        print("BM25 Top Match: No results found.")
    
    # 2. Semantic Search
    # Convert query text to embedding vector first
    query_vector = embedder.embed_batch([q])[0] 
    
    # Call search with the vector
    semantic_res = vs.search(query_vector, top_k=1)
    
    if semantic_res:
        # Check if the result is a list and access the payload
        # Note: Depending on your vs.search return type, you might need to adjust this
        match = semantic_res[0].payload if hasattr(semantic_res[0], 'payload') else semantic_res[0].get('payload')
        print(f"Semantic Top Match: {match.get('name', 'N/A')}")
    else:
        print("Semantic Top Match: No results found.")