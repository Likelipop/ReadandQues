import chromadb
import json

client = chromadb.HttpClient(host='localhost', port=8002)
collections = client.list_collections()

if not collections:
    print("No collections found.")
else:
    print(f"Found {len(collections)} collection(s):")
    for col in collections:
        print(f"\n==============================================")
        print(f"Collection: {col.name} (Total items: {col.count()})")
        print(f"==============================================")
        
        # Get up to 5 items
        results = col.get(limit=5)
        
        if not results['ids']:
            print("  (Empty collection)")
            continue
            
        for i in range(len(results['ids'])):
            print(f"\n--- ID: {results['ids'][i]} ---")
            
            # Print Metadata
            if results['metadatas'] and results['metadatas'][i]:
                print(f"Metadata:")
                for k, v in results['metadatas'][i].items():
                    print(f"  {k}: {v}")
            
            # Print Document
            if results['documents'] and results['documents'][i]:
                print(f"\nDocument snippet:")
                doc = results['documents'][i]
                # Truncate long documents
                if len(doc) > 200:
                    print(f"  {doc[:200]}...")
                else:
                    print(f"  {doc}")
