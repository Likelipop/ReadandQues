import chromadb
import random
import json

client = chromadb.HttpClient(host='localhost', port=8002)
col = client.get_collection("gold_semantic_chunks")

# Get all chunks
all_data = col.get()
ids = all_data['ids']
docs = all_data['documents']
metadatas = all_data['metadatas']

# Pick 5 random indices
indices = random.sample(range(len(ids)), 5)

results = []
for i in indices:
    results.append({
        "id": ids[i],
        "text": docs[i],
        "article_id": metadatas[i].get('article_id', '')
    })

print(json.dumps(results, indent=2))
