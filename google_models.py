from pymongo import MongoClient
from config.settings import settings
client = MongoClient(settings.mongodb_uri)
for doc in client[settings.mongodb_db][settings.mongodb_collection].find().limit(3):
    print(doc)
    print('---')
