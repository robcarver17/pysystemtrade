import pytest
from sysinit.futures.rollcalendars_from_db_prices_to_csv import (
    build_and_write_roll_calendar,
    check_saved_roll_calendar,
)
from sysdata.csv.csv_futures_contract_prices import csvFuturesContractPriceData
from sysdata.csv.csv_futures_contract_prices import ConfigCsvFuturesPrices
from sysdata.csv.csv_roll_parameters import csvRollParametersData


class TestFuturesInit:
    csv_config = ConfigCsvFuturesPrices(
        input_date_index_name="Time",
        input_skiprows=0,
        input_skipfooter=0,
        input_date_format="%Y-%m-%dT%H:%M:%S",
        input_column_mapping=dict(
            OPEN="Open", HIGH="High", LOW="Low", FINAL="Close", VOLUME="Volume"
        ),
    )

    def test_build_roll_calendar(self, tmp_path, monkeypatch):
        """
        Tests the function that builds roll calendars from individual contract prices. Mocks user input
        and writes output to temp file
        """

        monkeypatch.setattr("builtins.input", lambda _: "AUD")

        sample_prices = csvFuturesContractPriceData(
            datapath="sysinit.futures.tests.price", config=self.csv_config
        )
        output_dir = str(tmp_path)

        build_and_write_roll_calendar(
            "AUD",
            output_datapath=output_dir,
            input_prices=sample_prices,
            roll_parameters_data=csvRollParametersData(),
            check_before_writing=False,
        )

    def test_check_saved_roll_calendar(self):
        """
        Tests the function that checks a roll calendar generated from individual contract prices
        """
        sample_prices = csvFuturesContractPriceData(
            datapath="sysinit.futures.tests.price", config=self.csv_config
        )

        check_saved_roll_calendar(
            "AUD",
            input_datapath="sysinit.futures.tests.roll_cal",
            input_prices=sample_prices,
        )
