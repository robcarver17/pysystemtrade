from sysdata.mongodb.mongo_connection import mongoConnection, mongoDb


if __name__ == '__main__':


    # 1. Get instance
    mongo_instance = mongoDb()
    print(mongo_instance)

    # 2. Get collection
    # mongo_conn = mongoConnection("spread_costs") # rep as db
    # print(mongo_conn.collection)
