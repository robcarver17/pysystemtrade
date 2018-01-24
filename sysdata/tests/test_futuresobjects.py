import unittest
import datetime
from sysdata.futuresdata import rollCycle, futuresInstrument, contractDate, NO_DAY_DEFINED, NO_ROLL_CYCLE, NO_EXPIRY_DATE, futuresContract, listOfFuturesContracts

class MyTestCase(unittest.TestCase):
    def test_rollcycle(self):

        cycle1 = rollCycle("HMUZ")

        self.assertEqual(cycle1.as_list(), [3,6,9,12])

        ## check moving forwards and backwards
        self.assertEqual(cycle1.offset_month("H",1), "M")
        self.assertEqual(cycle1.offset_month("H", -1), "Z")
        self.assertEqual(cycle1.offset_month("Z", -1), "U")
        self.assertEqual(cycle1.offset_month("Z", 1), "H")
        self.assertEqual(cycle1.offset_month("M", 4), "M")

        self.assertEqual(cycle1.previous_month("H"), "Z")
        self.assertEqual(cycle1.previous_month("Z"), "U")
        self.assertEqual(cycle1.next_month("Z"), "H")
        self.assertEqual(cycle1.next_month("H"), "M")

        self.assertEqual(cycle1.where_month("H"), 0)
        self.assertEqual(cycle1.where_month("Z"), 3)

        self.assertEqual(cycle1.month_is_first("H"), True)
        self.assertEqual(cycle1.month_is_first("Z"), False)

        self.assertEqual(cycle1.month_is_last("H"), False)
        self.assertEqual(cycle1.month_is_last("Z"), True)

        self.assertEqual(cycle1.check_is_month_in_rollcycle("H"), True)
        self.assertRaises(Exception, cycle1.check_is_month_in_rollcycle, "J")

        self.assertRaises(Exception, cycle1.month_is_first, "J")

    def test_futuresInstrument(self):

        instrument = futuresInstrument("EDOLLAR")
        self.assertEqual(instrument.instrument_code, "EDOLLAR")

    def test_contractDate(self):

        contract_date201801=contractDate("201801")
        contract_date20180115=contractDate("20180115")


        # basic functionality
        self.assertEqual(contract_date201801.contract_date, "20180100")
        self.assertEqual(contract_date20180115.contract_date, "20180115")

        self.assertEqual(contract_date201801.year(), 2018)
        self.assertEqual(contract_date201801.month(), 1)
        self.assertEqual(contract_date201801.day(), NO_DAY_DEFINED)

        self.assertEqual(contract_date20180115.day(), 15)

        self.assertEqual(contract_date201801.letter_month(), "F")
        self.assertEqual(contract_date201801.as_date(), datetime.datetime(2018,1,1))
        self.assertEqual(contract_date20180115.as_date(), datetime.datetime(2018,1,15))

        # check date comparision
        self.assertEqual(contract_date201801.check_if_contract_signature_after_date(datetime.datetime(2018,2,1)), False)
        self.assertEqual(contract_date201801.check_if_contract_signature_after_date(datetime.datetime(2017,12,31)), True)

        # alternative method to define contracts
        contract_date201801b = contractDate.contract_date_from_numbers(2018,1)
        contract_date20180115b = contractDate.contract_date_from_numbers(2018,1, 15)

        self.assertEqual(contract_date201801b.contract_date, "20180100")
        self.assertEqual(contract_date20180115b.contract_date, "20180115")

        # check expiry dates
        contract_date201803_withexpiry=contractDate("201803", expiry_date=datetime.datetime(2008,3,15))
        contract_date201801b_withexpiry = contractDate.contract_date_from_numbers(2018,1,
                                                                                  expiry_date = datetime.datetime(2008,1,16))

        self.assertEqual(contract_date201803_withexpiry.expiry_date, datetime.datetime(2008,3,15))
        self.assertEqual(contract_date201801b_withexpiry.expiry_date, datetime.datetime(2008,1,16))

        # check roll cycles
        self.assertEqual(contract_date201801.rollcycle, NO_ROLL_CYCLE)
        contract_date201803_withrolls = contractDate("201803", rollcycle_string="HMUZ")
        self.assertEqual(contract_date201803_withrolls.rollcycle.as_list(), [3,6,9,12])

        # can add roll cycle as property
        contract_date201801.rollcycle = "F"
        self.assertEqual(contract_date201801.rollcycle.as_list(), [1])

        # can't include date that doesn't fit in roll cycle
        self.assertRaises(Exception, contractDate, "201801", rollcycle_string="HMUZ")

        # check we can move forward
        contract_date201806_withrolls = contract_date201803_withrolls.next_contract_date()
        self.assertEqual(contract_date201806_withrolls.contract_date, "20180600")
        self.assertEqual(contract_date201806_withrolls.rollcycle.as_list(), contract_date201803_withrolls.rollcycle.as_list())

        # check we can move back
        contract_date201803_withrolls_derived = contract_date201806_withrolls.previous_contract_date()
        self.assertEqual(contract_date201803_withrolls_derived.contract_date, "20180300")
        self.assertEqual(contract_date201803_withrolls_derived.rollcycle.as_list(),
                         contract_date201803_withrolls.rollcycle.as_list())

        ## EXPIRY DATE should vanish on moving forward
        contract_date201803_withexpiry.rollcycle = "HMUZ"
        self.assertEqual(contract_date201803_withexpiry.expiry_date, datetime.datetime(2008,3,15))

        contract_date201806_withrolls_expiry = contract_date201803_withexpiry.next_contract_date()
        self.assertEqual(contract_date201806_withrolls_expiry.expiry_date, NO_EXPIRY_DATE)

        # moving forward corner case
        contract_date201812 = contractDate("201812", rollcycle_string="HMUZ")
        contract_date201903 = contract_date201812.next_contract_date()
        self.assertEqual(contract_date201903.contract_date, "20190300")

        # moving back corner case
        contract_date201903 = contractDate("201903", rollcycle_string="HMUZ")
        contract_date201812_derived = contract_date201903.previous_contract_date()
        self.assertEqual(contract_date201812_derived.contract_date, "20181200")

        # moving forward with day attached
        contract_date20181215 = contractDate("20181215", rollcycle_string="HMUZ")
        contract_date20190315 = contract_date20181215.next_contract_date()
        self.assertEqual(contract_date20190315.contract_date, "20190315")

        # first contract date,
        contract_date197003=contractDate.approx_first_contractDate_after_date(datetime.datetime(1970, 1, 1), "HMUZ")
        self.assertEqual(contract_date197003.contract_date, "19700300")

        # check expiry date vanishes
        self.assertEqual(contract_date197003.expiry_date, NO_EXPIRY_DATE)

        # corner cases
        contract_date197003=contractDate.approx_first_contractDate_after_date(datetime.datetime(1970, 12, 1), "HMUZ")
        self.assertEqual(contract_date197003.contract_date, "19710300")

        contract_date197102=contractDate.approx_first_contractDate_after_date(datetime.datetime(1970, 12, 1), "GHMUZ")
        self.assertEqual(contract_date197102.contract_date, "19710200")




    def test_futuresContract(self):

        contract1 = futuresContract.simple("EDOLLAR", "201812", rollcycle_string = "HMUZ")

        self.assertEqual(contract1.date.rollcycle.cyclestring, "HMUZ")
        self.assertEqual(contract1.contract_date, "20181200")
        self.assertEqual(contract1.instrument_code, "EDOLLAR")
        self.assertEqual(contract1.expiry_date, NO_EXPIRY_DATE)
        self.assertEqual(contract1.rollcycle_string, "HMUZ")

        contract2 = futuresContract.simple("EDOLLAR", "20181215", expiry_date=datetime.datetime(2018,12,15))
        self.assertEqual(contract2.expiry_date, datetime.datetime(2018,12,15))
        self.assertEqual(contract2.contract_date, "20181215")
        self.assertEqual(contract2.date.rollcycle, NO_ROLL_CYCLE)

        contract1a=contract1.next_contract()
        self.assertEqual(contract1a.contract_date, "20190300")

        contract1b=contract1.previous_contract()
        self.assertEqual(contract1b.contract_date, "20180900")

        contract3=futuresContract.approx_first_futuresContract_after_date("EDOLLAR", datetime.datetime(1970, 12, 1), "HMUZ")
        self.assertEqual(contract3.contract_date, "19710300")

        list_of_contracts = listOfFuturesContracts.series_of_contracts_within_daterange("EDOLLAR",
                                                                datetime.datetime(2016,1,1), datetime.datetime(2018,1,1),
                                                                rollcycle_string="HMUZ")


if __name__ == '__main__':
    unittest.main()
