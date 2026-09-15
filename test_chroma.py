import chromadb
client = chromadb.HttpClient(host='localhost', port=8002)
cols = client.list_collections()
for c in cols:
    print("Name:", c.name)
    print("Count:", c.count())
    print("Peek ids:", c.peek(1)['ids'])
