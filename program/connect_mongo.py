from sysdata.mongodb.mongo_connection import mongoConnection, mongoDb

if __name__ == '__main__':

    # Select collection
    # mongo_conn = mongoConnection("spread_costs") # rep as db
    # print(mongo_conn.collection)


    a = mongoDb()
    print(a)
