import urllib.request
from pymongo import MongoClient

client = MongoClient("mongodb://admin:changeme@localhost:27017/")
db = client["articles"]
gold_col = db["gold_articles"]

doc = gold_col.find_one({"status": "completed"})
article_id = str(doc["_id"])
print(f"Testing with article ID: {article_id}")

try:
    url = f"http://localhost:8000/articles/{article_id}/"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as response:
        html = response.read().decode('utf-8')
        print(html[:500])
except Exception as e:
    print(f"Error fetching URL: {e}")
