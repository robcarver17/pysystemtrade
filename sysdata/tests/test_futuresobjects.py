import pandas as pd
import unittest
import datetime
from sysdata.futures.rolls import (
    rollCycle_TOMOVE,
    rollParametersTOMOVE,
    contractDateWithRollParametersTOMOVE,
)
from sysobjects.contract_dates_and_expiries import contractDate
from sysobjects.contracts import futuresContract, listOfFuturesContracts
from sysobjects.instruments import futuresInstrument


class MyTestCase(unittest.TestCase):
    def test_rollcycle(self):

        cycle1 = rollCycle_TOMOVE("HMUZ")
        self.assertEqual(cycle1.__repr__(), "HMUZ")

        self.assertEqual(cycle1._as_list(), [3, 6, 9, 12])

        # check moving forwards and backwards
        self.assertEqual(cycle1._offset_month("H", 1), "M")
        self.assertEqual(cycle1._offset_month("H", -1), "Z")
        self.assertEqual(cycle1._offset_month("Z", -1), "U")
        self.assertEqual(cycle1._offset_month("Z", 1), "H")
        self.assertEqual(cycle1._offset_month("M", 4), "M")

        self.assertEqual(cycle1._previous_month("H"), "Z")
        self.assertEqual(cycle1._previous_month("Z"), "U")
        self.assertEqual(cycle1._next_month("Z"), "H")
        self.assertEqual(cycle1._next_month("H"), "M")

        self.assertEqual(cycle1._where_month("H"), 0)
        self.assertEqual(cycle1._where_month("Z"), 3)

        self.assertEqual(cycle1._month_is_first("H"), True)
        self.assertEqual(cycle1._month_is_first("Z"), False)

        self.assertEqual(cycle1._month_is_last("H"), False)
        self.assertEqual(cycle1._month_is_last("Z"), True)

        self.assertEqual(cycle1._check_is_month_in_rollcycle("H"), True)
        self.assertRaises(Exception, cycle1._check_is_month_in_rollcycle, "J")

        self.assertRaises(Exception, cycle1._month_is_first, "J")

        self.assertEqual(cycle1._previous_year_month(2002, "M"), (2002, "H"))
        self.assertEqual(cycle1._previous_year_month(2002, "H"), (2001, "Z"))

        self.assertEqual(cycle1._next_year_month(2002, "M"), (2002, "U"))
        self.assertEqual(cycle1._next_year_month(2002, "Z"), (2003, "H"))

        self.assertEqual(
            cycle1.yearmonth_inrollcycle_after_date(
                datetime.datetime(
                    2002, 1, 1)), (2002, 3), )
        self.assertEqual(
            cycle1.yearmonth_inrollcycle_after_date(
                datetime.datetime(
                    2002, 12, 1)), (2003, 3), )
        self.assertEqual(
            cycle1.yearmonth_inrollcycle_after_date(
                datetime.datetime(
                    2002, 12, 31)), (2003, 3), )
        self.assertEqual(
            cycle1.yearmonth_inrollcycle_after_date(
                datetime.datetime(
                    2002, 3, 1)), (2002, 6), )
        self.assertEqual(
            cycle1.yearmonth_inrollcycle_after_date(
                datetime.datetime(
                    2002, 5, 31)), (2002, 6), )

        self.assertEqual(
            cycle1.yearmonth_inrollcycle_before_date(
                datetime.datetime(
                    2002, 1, 1)), (2001, 12), )
        self.assertEqual(
            cycle1.yearmonth_inrollcycle_before_date(
                datetime.datetime(
                    2002, 3, 1)), (2001, 12), )
        self.assertEqual(
            cycle1.yearmonth_inrollcycle_before_date(
                datetime.datetime(
                    2002, 4, 1)), (2002, 3), )
        self.assertEqual(
            cycle1.yearmonth_inrollcycle_before_date(
                datetime.datetime(
                    2002, 5, 31)), (2002, 3), )

    def test_rolldata(self):
        roll_data_blank = rollParametersTOMOVE()

        self.assertRaises(Exception, roll_data_blank.check_for_price_cycle)
        self.assertRaises(Exception, roll_data_blank.check_for_hold_cycle)

        roll_data_empty = rollParametersTOMOVE.create_empty()
        self.assertEqual(roll_data_empty.empty(), True)

        roll_data = rollParametersTOMOVE(
            priced_rollcycle="HMUZ",
            hold_rollcycle="Z",
            approx_expiry_offset=15)

        contract_date = roll_data.approx_first_held_contractDate_at_date(
            datetime.datetime(2008, 1, 1)
        )
        self.assertEqual(contract_date.date, "20081200")
        self.assertEqual(
            contract_date.expiry_date,
            datetime.datetime(
                2008,
                12,
                16))

        roll_data = rollParametersTOMOVE(
            priced_rollcycle="HMUZ",
            hold_rollcycle="HMUZ",
            roll_offset_day=-365)

        contract_date_held = roll_data.approx_first_held_contractDate_at_date(
            datetime.datetime(2008, 1, 1)
        )
        self.assertEqual(contract_date_held.date, "20090300")
        self.assertEqual(contract_date_held.expiry_date,
                         datetime.datetime(2009, 3, 1))

    def test_roll_with_date(self):
        roll_data = rollParametersTOMOVE(
            priced_rollcycle="HMUZ",
            hold_rollcycle="Z",
            approx_expiry_offset=15)
        rollwithdate = contractDateWithRollParametersTOMOVE(roll_data, "201801")

        self.assertRaises(Exception, rollwithdate.next_priced_contract)

        roll_data_no_price_cycle = rollParametersTOMOVE(
            hold_rollcycle="F", approx_expiry_offset=15
        )
        rollwithdate = contractDateWithRollParametersTOMOVE(roll_data, "201801")

        self.assertRaises(Exception, rollwithdate.next_priced_contract)

        roll_data = rollParametersTOMOVE(
            priced_rollcycle="HMUZ",
            hold_rollcycle="MZ",
            approx_expiry_offset=15)
        rollwithdate = contractDateWithRollParametersTOMOVE(roll_data, "201806")

        self.assertEqual(rollwithdate.date, "20180600")
        self.assertEqual(
            rollwithdate.expiry_date,
            datetime.datetime(
                2018,
                6,
                16))
        self.assertEqual(
            rollwithdate.check_if_expiry_after_date(
                datetime.datetime(
                    2018, 1, 1)), True)

        next_held = rollwithdate.next_held_contract()
        prior_held = rollwithdate.previous_held_contract()

        next_priced = rollwithdate.next_priced_contract()
        prior_priced = rollwithdate.previous_priced_contract()

        self.assertEqual(next_held.date, "20181200")
        self.assertEqual(prior_held.date, "20171200")
        self.assertEqual(next_priced.date, "20180900")
        self.assertEqual(prior_priced.date, "20180300")

    def test_futuresInstrument(self):

        instrument = futuresInstrument("EDOLLAR")
        self.assertEqual(instrument.instrument_code, "EDOLLAR")

        instrument_dict = instrument.as_dict()
        print(instrument_dict)
        self.assertEqual(instrument_dict["instrument_code"], "EDOLLAR")

        new_instrument = instrument.create_from_dict(instrument_dict)
        self.assertEqual(new_instrument.instrument_code, "EDOLLAR")

    def test_contractDate(self):

        contract_date201801 = contractDate("201801")
        contract_date20180115 = contractDate("20180115")

        contract_date20180100 = contractDate("20180100")
        self.assertEqual(contract_date20180100.date, "20180100")

        # dictionary
        contract_date_dict_201801 = contract_date201801.as_dict()
        self.assertEqual(
            contract_date_dict_201801,
            dict(
                expiry_date=(
                    2018,
                    1,
                    1),
                contract_date="201801",
                approx_expiry_offset=0),
        )

        contract_date_dict_20180115 = contract_date20180115.as_dict()
        self.assertEqual(
            contract_date_dict_20180115,
            dict(
                expiry_date=(2018, 1, 15),
                contract_date="20180115",
                approx_expiry_offset=0,
            ),
        )

        new_contractdate20801 = contractDate.create_from_dict(
            contract_date_dict_201801)
        self.assertEqual(
            contract_date201801.date,
            new_contractdate20801.date)
        self.assertEqual(
            contract_date201801.expiry_date.year,
            new_contractdate20801.expiry_date.year)

        # basic functionality
        self.assertEqual(contract_date201801.date, "20180100")
        self.assertEqual(contract_date20180115.date, "20180115")

        self.assertEqual(contract_date201801.year(), 2018)
        self.assertEqual(contract_date201801.month(), 1)
        self.assertEqual(contract_date201801.only_has_month, True)

        self.assertEqual(contract_date20180115.day(), 15)

        self.assertEqual(contract_date201801.letter_month(), "F")
        self.assertEqual(contract_date201801._as_date(),
                         datetime.datetime(2018, 1, 1))
        self.assertEqual(
            contract_date20180115._as_date(), datetime.datetime(2018, 1, 15)
        )

        # check date comparision
        self.assertEqual(
            contract_date201801.check_if_expiry_after_date(
                datetime.datetime(2018, 2, 1)
            ),
            False,
        )
        self.assertEqual(
            contract_date201801.check_if_expiry_after_date(
                datetime.datetime(2017, 12, 31)
            ),
            True,
        )

        # alternative method to define contracts
        contract_date201801b = contractDate.contract_date_from_numbers(2018, 1)
        contract_date20180115b = contractDate.contract_date_from_numbers(
            2018, 1, 15)

        self.assertEqual(contract_date201801b.date, "20180100")
        self.assertEqual(contract_date20180115b.date, "20180115")

        # check expiry dates
        contract_date201803_withexpiry = contractDate(
            "201803", expiry_date=(2008, 3, 15)
        )
        contract_date201801b_withexpiry = contractDate.contract_date_from_numbers(
            2018, 1, expiry_date=(2008, 1, 16))

        self.assertEqual(
            contract_date201803_withexpiry.expiry_date,
            datetime.datetime(
                2008,
                3,
                15))
        self.assertEqual(
            contract_date201801b_withexpiry.expiry_date,
            datetime.datetime(
                2008,
                1,
                16))

        # check expiry dates with contract offset
        contract_date201803_withexpiry_offset = contractDate(
            "201803", approx_expiry_offset=40
        )
        contract_date201801b_withexpiry_offset = (
            contractDate.contract_date_from_numbers(
                2018, 1, approx_expiry_offset=-20))

        self.assertEqual(
            contract_date201803_withexpiry_offset.expiry_date,
            datetime.datetime(2018, 4, 10),
        )
        self.assertEqual(
            contract_date201801b_withexpiry_offset.expiry_date,
            datetime.datetime(2017, 12, 12),
        )

    def test_futuresContract(self):

        contract0 = futuresContract(futuresInstrument.create_empty(), "201801")

        contract1 = futuresContract.simple("EDOLLAR", "201812")

        self.assertEqual(contract1.date, "20181200")
        self.assertEqual(contract1.instrument_code, "EDOLLAR")
        self.assertTrue(contract1.expiry_date, datetime.datetime(2018, 12, 1))

        # dictionaries
        contract1_as_dict = contract1.as_dict()
        self.assertEqual(
            contract1_as_dict,
            dict(
                instrument_code="EDOLLAR",
                expiry_date=(2018, 12, 1),
                contract_date="201812",
                approx_expiry_offset=0,
            ),
        )

        contract1_fromdict = futuresContract.create_from_dict(
            contract1_as_dict)

        self.assertEqual(contract1_fromdict.instrument_code, "EDOLLAR")
        self.assertEqual(contract1_fromdict.expiry_date,
                         datetime.datetime(2018, 12, 1))
        self.assertEqual(contract1_fromdict.date, "20181200")

        contract2 = futuresContract.simple(
            "EDOLLAR", "20181215", expiry_date=(2018, 12, 15)
        )
        self.assertEqual(
            contract2.expiry_date,
            datetime.datetime(
                2018,
                12,
                15))
        self.assertEqual(contract2.date, "20181215")

        contract3 = futuresContract.simple(
            "EDOLLAR", "20181215", approx_expiry_offset=4
        )
        self.assertEqual(
            contract3.expiry_date,
            datetime.datetime(
                2018,
                12,
                19))

        # rolling
        contract1_with_roll_data = futuresContract.create_from_dict_with_rolldata(
            dict(
                instrument_code="EDOLLAR", contract_date="201812"), dict(
                priced_rollcycle="HMUZ", hold_rollcycle="Z", carry_offset=1), )

        contract1a = contract1_with_roll_data.next_priced_contract()
        self.assertEqual(contract1a.date, "20190300")

        contract1b = contract1_with_roll_data.previous_priced_contract()
        self.assertEqual(contract1b.date, "20180900")

        contract1c = contract1_with_roll_data.carry_contract()
        self.assertEqual(contract1c.date, "20190300")

        contract1d = contract1_with_roll_data.next_held_contract()
        self.assertEqual(contract1d.date, "20191200")

        contract1e = contract1_with_roll_data.previous_held_contract()
        self.assertEqual(contract1e.date, "20171200")

        contract_ident = futuresContract.identGivenCodeAndContractDate(
            "EDOLLAR", "201801"
        )
        self.assertEqual(contract_ident, "EDOLLAR/20180100")

    def test_list_of_futures_contracts(self):
        instrument_object = futuresInstrument("EDOLLAR")
        roll_parameters = rollParametersTOMOVE(
            priced_rollcycle="HMUZ",
            hold_rollcycle="MZ",
            approx_expiry_offset=15,
            roll_offset_day=-70,
        )
        flist = listOfFuturesContracts.historical_price_contracts(
            instrument_object, roll_parameters, "200003", pd.datetime(2001, 1, 1)
        )

        self.assertEqual(len(flist), 5)
        self.assertEqual(flist[0].date, "20000300")
        self.assertEqual(flist[-1].date, "20010300")


if __name__ == "__main__":
    unittest.main()
