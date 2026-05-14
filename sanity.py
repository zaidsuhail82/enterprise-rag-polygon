from qdrant_client import QdrantClient
client = QdrantClient(url="http://localhost:6333")
count = client.count(collection_name="enterprise_docs", exact=True)
print(f"Total points in Qdrant: {count.count}")

import pickle
with open('data/bm25_index.pkl', 'rb') as f:
    state = pickle.load(f)
print(f"Number of payloads: {len(state['payloads'])}")
# Print the first one to see if 'chunk_text' exists
if len(state['payloads']) > 0:
    print(f"Sample payload keys: {state['payloads'][0].keys()}")

# scripts/debug_metadata.py
from src.retrieval.vector_store import VectorStore

vs = VectorStore()
# Fetch a sample
sample = vs._client.scroll(collection_name="enterprise_docs", limit=5)
for point in sample[0]:
    print(f"Doc: {point.payload.get('document_name')}")
    print(f"Last Modified: {point.payload.get('last_modified')}")
    print(f"Type: {type(point.payload.get('last_modified'))}")