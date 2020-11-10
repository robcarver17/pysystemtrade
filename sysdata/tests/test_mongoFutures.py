import unittest
from sysdata.mongodb.mongo_futures_instruments import mongoFuturesInstrumentData
from sysdata.futures.rolls import rollParametersTOMOVE
from sysdata.mongodb.mongo_roll_data import mongoRollParametersData

from sysobjects.instruments import futuresInstrument


class MyTestCase(unittest.TestCase):
    def test_futures_instruments(self):
        data = mongoFuturesInstrumentData(database_name="test")

        # test db so okay to do this
        data._mongo.db.drop_collection(data._mongo.collection_name)

        codes = data.get_list_of_instruments()
        self.assertEqual(codes, [])

        instrument_object = data.get_instrument_data("EDOLLAR")

        self.assertTrue(instrument_object.empty())

        instrument_object = futuresInstrument("EDOLLAR", some_data="test")
        data.add_instrument_data(instrument_object)

        self.assertEqual(data.get_list_of_instruments(), ["EDOLLAR"])

        found_object = data.get_instrument_data("EDOLLAR")
        self.assertEqual(found_object.instrument_code, "EDOLLAR")

        found_object = data["EDOLLAR"]
        self.assertEqual(found_object.instrument_code, "EDOLLAR")

        self.assertEqual(found_object.meta_data["some_data"], "test")

        codes = data.get_list_of_instruments()
        self.assertEqual(codes, ["EDOLLAR"])

        data.delete_instrument_data("EDOLLAR", are_you_sure=True)

        instrument_object = data.get_instrument_data("EDOLLAR")

        self.assertTrue(instrument_object.empty())
        codes = data.get_list_of_instruments()
        self.assertEqual(codes, [])

    def test_roll_parameters(self):
        data = mongoRollParametersData(database_name="test")

        # test db so okay to do this
        data._mongo.db.drop_collection(data._mongo.collection_name)

        codes = data.get_list_of_instruments()
        self.assertEqual(codes, [])

        roll_object = data.get_roll_parameters("EDOLLAR")

        self.assertTrue(roll_object.empty())

        roll_object = rollParametersTOMOVE(
            hold_rollcycle="HMUZ",
            priced_rollcycle="HM")
        data.add_roll_parameters(roll_object, "EDOLLAR")

        self.assertEqual(data.get_list_of_instruments(), ["EDOLLAR"])

        found_object = data.get_roll_parameters("EDOLLAR")
        self.assertEqual(found_object.hold_rollcycle.cyclestring, "HMUZ")

        found_object = data["EDOLLAR"]
        self.assertEqual(found_object.priced_rollcycle.cyclestring, "HM")

        codes = data.get_list_of_instruments()
        self.assertEqual(codes, ["EDOLLAR"])

        data.delete_roll_parameters("EDOLLAR", are_you_sure=True)

        found_object = data.get_roll_parameters("EDOLLAR")

        self.assertTrue(found_object.empty())
        codes = data.get_list_of_instruments()
        self.assertEqual(codes, [])

    """
    def test_futures_contracts(self):
        data = mongoFuturesContractData(database_name="test")

        # This is fine for test data
        data._mongo.db.drop_collection(data._mongo.collection_name)

        contract_dates = data.get_list_of_contract_dates_for_instrument_code("EDOLLAR")
        self.assertEqual(contract_dates, [])
        contract_object = data.get_contract_data("EDOLLAR", "201801")
        self.assertTrue(contract_object.empty())
        self.assertEqual(data.is_contract_in_data("EDOLLAR", "201801"), False)

        contract_object1 = futuresContract(futuresInstrument("EDOLLAR"), contractDate("201801"))
        contract_object2 = futuresContract(futuresInstrument("EDOLLAR"), contractDate("20180115"))
        contract_object3 = futuresContract(futuresInstrument("CORN"), contractDate("201806", rollcycle_string="HMUZ"))
        contract_object4 = futuresContract(futuresInstrument("CORN"), contractDate("201809", expiry_date=(2018,1,1)))

        data.add_contract_data(contract_object1)
        data.add_contract_data(contract_object2)
        data.add_contract_data(contract_object3)
        data.add_contract_data(contract_object4)

        contract_dates = data.get_list_of_contract_dates_for_instrument_code("EDOLLAR")
        self.assertEqual(contract_dates, ['201801', '20180115'])
        contract_dates = data.get_list_of_contract_dates_for_instrument_code("CORN")
        self.assertEqual(contract_dates, ['201806', '201809'])
        contract_dates = data.get_list_of_contract_dates_for_instrument_code("Blimey governor")
        self.assertEqual(contract_dates, [])

        retrieve_contract1 = data.get_contract_data("EDOLLAR", "201801")
        retrieve_contract1b = data[("EDOLLAR", "201801")]
        retrieve_contract2 = data.get_contract_data("EDOLLAR", "20180115")
        retrieve_contract3 = data.get_contract_data("CORN", "201806")
        retrieve_contract4 = data.get_contract_data("CORN", "201809")
        retrieve_contract_non_existent = data.get_contract_data("EDOLLAR", "201803")

        self.assertEqual(retrieve_contract1.instrument_code, "EDOLLAR")
        self.assertEqual(retrieve_contract1b.contract_date, "20180100")

        self.assertTrue(retrieve_contract1.date.rollcycle.empty())
        self.assertTrue(retrieve_contract1.expiry_date.empty())
        self.assertEqual(retrieve_contract2.contract_date, "20180115")
        self.assertEqual(retrieve_contract3.instrument_code, "CORN")
        self.assertEqual(retrieve_contract3.rollcycle_string, "HMUZ")
        self.assertEqual(retrieve_contract4.expiry_date.month, 1)
        self.assertTrue(retrieve_contract_non_existent.empty())

        data.delete_contract_data("EDOLLAR", "201801", are_you_sure=True)
        contract_dates = data.get_list_of_contract_dates_for_instrument_code("EDOLLAR")
        self.assertEqual(contract_dates, ['20180115'])

        data.delete_contract_data("EDOLLAR", "20180115", are_you_sure=True)
        contract_dates = data.get_list_of_contract_dates_for_instrument_code("EDOLLAR")
        self.assertEqual(contract_dates, [])
        contract_dates = data.get_list_of_contract_dates_for_instrument_code("CORN")
        self.assertEqual(contract_dates, ['201806', '201809'])

        data.delete_contract_data("CORN", "201806", are_you_sure=True)
        data.delete_contract_data("CORN", "201809", are_you_sure=True)

        contract_dates = data.get_list_of_contract_dates_for_instrument_code("CORN")
        self.assertEqual(contract_dates, [])


if __name__ == '__main__':
    unittest.main()
    """
