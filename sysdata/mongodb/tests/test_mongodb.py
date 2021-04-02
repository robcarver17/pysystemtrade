from sysdata.mongodb.mongo_connection import clean_mongo_host


class TestMongoDB:

    def test_hide_password(self):

        # examples from https://docs.mongodb.com/manual/reference/connection-string/

        #host_pattern = re.compile('^(mongodb://)([^:]+):([^@]+)@([^/]+)')

        standalone = "mongodb://myDBReader:D1fficultP%40ssw0rd@mongodb0.example.com:27017/?authSource=admin"
        clean_standalone = clean_mongo_host(standalone)
        print(clean_standalone)
        assert 'D1fficultP%40ssw0rd' not in clean_standalone

        replica = "mongodb://myDBReader:D1fficultP%40ssw0rd@mongodb0.example.com:27017,mongodb1.example.com:27017,mongodb2.example.com:27017/?authSource=admin&replicaSet=myRepl"
        clean_replica = clean_mongo_host(replica)
        print(clean_replica)
        assert 'D1fficultP%40ssw0rd' not in clean_replica

        sharded = "mongodb://myDBReader:D1fficultP%40ssw0rd@mongos0.example.com:27017,mongos1.example.com:27017,mongos2.example.com:27017/?authSource=admin"
        clean_sharded = clean_mongo_host(sharded)
        print(clean_sharded)
        assert 'D1fficultP%40ssw0rd' not in clean_sharded
