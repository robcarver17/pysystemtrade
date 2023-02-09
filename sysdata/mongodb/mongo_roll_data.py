from syscore.exceptions import missingData
from sysdata.futures.rolls_parameters import rollParametersData
from sysobjects.rolls import rollParameters

from sysdata.mongodb.mongo_generic import mongoDataWithSingleKey
from syslogdiag.log_to_screen import logtoscreen
from syscore.constants import arg_not_supplied

ROLL_COLLECTION = "futures_roll_parameters"


class mongoRollParametersData(rollParametersData):
    """
    Read and write data class to get roll data


    """

    def __init__(
        self, mongo_db=arg_not_supplied, log=logtoscreen("mongoRollParametersData")
    ):
        super().__init__(log=log)
        self._mongo_data = mongoDataWithSingleKey(
            ROLL_COLLECTION, "instrument_code", mongo_db=mongo_db
        )

    def __repr__(self):
        return "mongoRollParametersData %s" % str(self.mongo_data)

    @property
    def mongo_data(self):
        return self._mongo_data

    def get_list_of_instruments(self) -> list:
        return self.mongo_data.get_list_of_keys()

    def _get_roll_parameters_without_checking(
        self, instrument_code: str
    ) -> rollParameters:
        try:
            result_dict = self.mongo_data.get_result_dict_for_key_without_key_value(
                instrument_code
            )
        except missingData:
            self.log.critical(
                "%s just vanished from roll parameters??" % instrument_code
            )
            raise

        roll_parameters_object = rollParameters.create_from_dict(result_dict)

        return roll_parameters_object

    def _delete_roll_parameters_data_without_any_warning_be_careful(
        self, instrument_code: str
    ):
        self.mongo_data.delete_data_without_any_warning(instrument_code)

    def _add_roll_parameters_without_checking_for_existing_entry(
        self, instrument_code: str, roll_parameters: rollParameters
    ):

        roll_parameters_object_dict = roll_parameters.as_dict()
        self.mongo_data.add_data(
            instrument_code, roll_parameters_object_dict, allow_overwrite=True
        )
