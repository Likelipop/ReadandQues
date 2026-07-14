from pymongo import MongoClient
from django.conf import settings
from pymongo.server_api import ServerApi

def get_mongo_db():
    # Ví dụ bạn cấu hình MONGO_URI = "mongodb://localhost:27017/" trong settings.py
    client = MongoClient(getattr(settings, "MONGO_URI", "mongodb://localhost:27017/"), 
                         server_api=ServerApi('1') )
    

    # Tên database của bạn, ví dụ: english_quiz_db
    db = client[getattr(settings, "MONGO_DB_NAME", "default")]
    return db