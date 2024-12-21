from sysdata.mongodb.mongo_connection import mongoConnection, mongoDb


if __name__ == '__main__':


    # 1. Get instance
    mongo_instance = mongoDb()

    # 2. Get db
    db = mongo_instance.db

    # 3. Get collection
    collections = db.list_collection_names()

    # 4. Print all out
    for collection in collections:
        print(collection)

    # Note 2. Get specific collection
    # mongo_conn = mongoConnection("spread_costs") # rep as db
    # print(mongo_conn.collection)
