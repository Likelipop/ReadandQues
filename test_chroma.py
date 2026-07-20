import sys
import chromadb
from pathlib import Path

client = chromadb.HttpClient(host='localhost', port=8002)
col = client.get_or_create_collection("articles")
print("Count:", col.count())
