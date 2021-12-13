from sysdata.mongodb.mongo_connection import clean_mongo_host


class TestMongoDB:
    def test_hide_password(self):

        # url examples from https://docs.mongodb.com/manual/reference/connection-string/

        ip = "mongodb://127.0.0.1/production"
        clean_ip = clean_mongo_host(ip)
        print(clean_ip)
        assert clean_ip == ip

        simple = "mongodb://localhost/production"
        clean_simple = clean_mongo_host(simple)
        print(clean_simple)
        assert clean_simple == simple

        simple_pw = "mongodb://myDBReader:D1fficultP%40ssw0rd@localhost/production"
        clean_simple_pw = clean_mongo_host(simple_pw)
        print(clean_simple_pw)
        assert "D1fficultP%40ssw0rd" not in clean_simple_pw

        simple_port = "mongodb://localhost:28018/production"
        clean_simple_port = clean_mongo_host(simple_port)
        print(simple_port)
        assert clean_simple_port == simple_port

        standalone = "mongodb://myDBReader:D1fficultP%40ssw0rd@mongodb0.example.com:27017/?authSource=admin"
        clean_standalone = clean_mongo_host(standalone)
        print(clean_standalone)
        assert "D1fficultP%40ssw0rd" not in clean_standalone

        replica = "mongodb://myDBReader:D1fficultP%40ssw0rd@mongodb0.example.com:27017,mongodb1.example.com:27017,mongodb2.example.com:27017/?authSource=admin&replicaSet=myRepl"
        clean_replica = clean_mongo_host(replica)
        print(clean_replica)
        assert "D1fficultP%40ssw0rd" not in clean_replica

        sharded = "mongodb://myDBReader:D1fficultP%40ssw0rd@mongos0.example.com:27017,mongos1.example.com:27017,mongos2.example.com:27017/?authSource=admin"
        clean_sharded = clean_mongo_host(sharded)
        print(clean_sharded)
        assert "D1fficultP%40ssw0rd" not in clean_sharded
