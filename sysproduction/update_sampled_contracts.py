
from collections import namedtuple

from syscore.objects import missing_contract

from sysbrokers.IB.ibConnection import connectionIB
from sysbrokers.IB.ibFuturesContractPriceData import ibFuturesContractPriceData

from sysdata.mongodb.mongo_connection import mongoDb
from sysdata.mongodb.mongo_futures_contracts import mongoFuturesContractData
from sysdata.arctic.arctic_multiple_prices import arcticFuturesMultiplePricesData
from sysdata.mongodb.mongo_roll_data import mongoRollParametersData

from sysdata.futures.rolls import contractDateWithRollParameters
from sysdata.futures.contracts import futuresContract, listOfFuturesContracts
from sysdata.futures.instruments import futuresInstrument

from syslogdiag.log import logToMongod as logger
from syslogdiag.log import logtoscreen

dataBlob = namedtuple("DataBlob", "arctic_multiple_prices ib_futures_prices mongo_contract_data mongo_roll_data ib_conn")

def update_sampled_contracts():
    """
    Update the active contracts, according to what is available in IB for a given instrument

    These are stored in mongoDB

    The active contracts list is used to see what contracts have historical data sampled for

    It does not tell you what the current priced, forward, or carry contract are - that is in multiple prices (DRY)

    However we base the list of theoretical active contracts on the current priced, forward, and carry contracts

    We will end up adding to this list when we roll; this will change the current priced, forward, and carry contract

    When we add a new contract (because one has become available), we get the exact expiry date from IB and save this with the
       contract data.

    We do not sample contracts on the list when they have passed their expiry date

    Contracts are never deleted from the database

    We don't check IB for contracts; since we can't reverse engineer a YYYYMM identifier from a YYYYMMDD

    :returns: None
    """
    with mongoDb() as mongo_db,\
        logger("Update-Sampled_Contracts", mongo_db=mongo_db) as log,\
        connectionIB(log=log.setup(component="IB-connection")) as ib_conn:

        data = setup_data(mongo_db, ib_conn, log=log)

        list_of_codes_all = data.arctic_multiple_prices.get_list_of_instruments()
        for instrument_code in list_of_codes_all:
            new_log = log.setup(instrument_code = instrument_code)
            update_active_contracts_for_instrument(instrument_code, data, log=new_log)


def setup_data(mongo_db, ib_conn, log=logtoscreen("")):

    arctic_multiple_prices = arcticFuturesMultiplePricesData(mongo_db, log=log.setup(component="arcticMultiplePricesData"))
    ib_futures_prices = ibFuturesContractPriceData(ib_conn, log=log.setup(component="ibFuturesContractPriceData"))
    mongo_contract_data = mongoFuturesContractData(mongo_db, log=log.setup(component="mongoFuturesContractData"))
    mongo_roll_data = mongoRollParametersData(mongo_db, log=log.setup(component="mongoRollParametersData"))

    data=dataBlob(arctic_multiple_prices, ib_futures_prices, mongo_contract_data, mongo_roll_data, ib_conn)

    return data

def update_active_contracts_for_instrument(instrument_code, data, log=logtoscreen("")):
    # Get the list of contracts we'd want to get prices for, given current roll calendar
    required_contract_chain = get_contract_chain(instrument_code, data)

    # Make sure contract chain and database are aligned
    update_contract_database_with_contract_chain(instrument_code, required_contract_chain, data)

    # Now to check if expiry dates are resolved
    update_expiries_of_sampled_contracts(instrument_code, data)

    return None

def get_contract_chain(instrument_code, data):

    roll_parameters = data.mongo_roll_data.get_roll_parameters(instrument_code)

    # Get the last contract currently being used
    multiple_prices = data.arctic_multiple_prices.get_multiple_prices(instrument_code)
    current_contract_dict = multiple_prices.current_contract_dict()
    current_contract_list = list(current_contract_dict.values())
    furthest_out_contract_date = max(current_contract_list)
    furthest_out_contract = contractDateWithRollParameters(roll_parameters, furthest_out_contract_date)

    ## To give us wiggle room, and ensure we start collecting the new forward a little in advance
    final_contract = furthest_out_contract.next_priced_contract()

    contract_date_chain = final_contract.get_unexpired_contracts_from_now_to_contract_date()

    # We have a list of contract_date objects, need futureContracts
    # create a 'bare' instrument object
    instrument_object = futuresInstrument(instrument_code)

    contract_object_chain_as_list = [futuresContract(instrument_object, contract_date_object)
                             for contract_date_object in contract_date_chain]

    contract_object_chain = listOfFuturesContracts(contract_object_chain_as_list)

    return contract_object_chain

def update_contract_database_with_contract_chain( instrument_code, required_contract_chain, data, log=logtoscreen("")):
    """

    :param required_contract_chain: list of contract dates 'yyyymm'
    :param instrument_code: str
    :param data: dataBlob
    :return: None
    """

    # Get list of contracts in the database
    all_contracts_in_db = data.mongo_contract_data.get_all_contract_objects_for_instrument_code(instrument_code)
    current_contract_chain = all_contracts_in_db.currently_sampling()

    #Is something in required_contract_chain, but not in the database?
    missing_from_db = required_contract_chain.difference(current_contract_chain)

    #They have probably been added as the result of a recent roll
    # Let's add them
    add_missing_contracts_to_database(instrument_code, missing_from_db, data, log=log)

    #Is something in the database, but not in required_contract_chain?
    #Then it's eithier expired or weirdly very far in the future (maybe we changed the roll parameters)
    #Eithier way, we stop sampling it (if it hasn't expired, will be added in the future)
    contracts_not_sampling = current_contract_chain.difference(required_contract_chain)
    mark_contracts_as_stopped_sampling(instrument_code, contracts_not_sampling, data, log=log)

    return None

def add_missing_contracts_to_database(instrument_code, missing_from_db, data, log=logtoscreen("")):
    """

    :param instrument_code: str
    :param missing_from_db: list of contract_date objects
    :param data: dataBlob
    :return: None
    """

    for contract_to_add in missing_from_db:
        contract_date = contract_to_add.date
        if data.mongo_contract_data.is_contract_in_data(instrument_code, contract_date):
            contract_to_add = data.mongo_contract_data.get_contract_data(instrument_code, contract_date)

        # Mark it as sampling
        contract_to_add.sampling_on()

        #Add it to the database
        #We are happy to overwrite
        data.mongo_contract_data.add_contract_data(contract_to_add, ignore_duplication=True)

        log.msg("Contract %s now added to database and sampling" % str(contract_to_add))

    return None

def mark_contracts_as_stopped_sampling(instrument_code, contracts_not_sampling, data, log=logtoscreen("")):
    """

    :param instrument_code: str
    :param contracts_not_sampling: list of contractDate objects
    :param data: dataBlobg
    :return: None
    """
    for contract_date_object in contracts_not_sampling:
        contract_date = contract_date_object.date

        #Mark it as stop sampling in the database
        contract = data.mongo_contract_data.get_contract_data(instrument_code, contract_date)
        if contract.currently_sampling:
            contract.sampling_off()
            data.mongo_contract_data.add_contract_data(contract, ignore_duplication=True)

            log.msg("Contract %s has now stopped sampling" % str(contract), contract_date=contract.date)
        else:
            # nothing to do
            pass

    return None

def update_expiries_of_sampled_contracts(instrument_code, data, log=logtoscreen("")):
    """
    # Now to check if expiry dates are resolved
    # For everything in the database which is sampling
    #   - if it hasn't got an IB expiry recorded, then check for the expiry in IB (can fail)
    #    - if expiry found, add expiry to database, and flag in lookup table as found

    :param instrument_code:
    :param data: dataBlob
    :return: None
    """

    all_contracts_in_db = data.mongo_contract_data.get_all_contract_objects_for_instrument_code(instrument_code)
    currently_sampling_contracts = all_contracts_in_db.currently_sampling()

    for contract_object in currently_sampling_contracts:
        update_expiry_for_contract(contract_object, data, log=log)

    return None

def update_expiry_for_contract(contract_object, data, log=logtoscreen("")):
    """
    Get an expiry from IB, check if same as database, otherwise update the database

    :param contract_object: contract object
    :param data: dataBlob
    :param log: log
    :return: None
    """

    contract_date = contract_object.date
    instrument_code = contract_object.instrument_code

    db_contract = data.mongo_contract_data.get_contract_data(instrument_code, contract_date)

    # Both should be in format expiryDate(yyyy,mm,dd)
    db_expiry_date = db_contract.contract_date.expiry_date
    ib_expiry_date = data.ib_futures_prices.\
        get_actual_expiry_date_for_instrument_code_and_contract_date(instrument_code, contract_date)

    if ib_expiry_date is missing_contract:
        # We can do nothing with that...
        log.warn("Couldn't get expiry date for %s" % str(contract_object), contract_date=contract_object.date)
        return None

    ## Will they be same format?
    if ib_expiry_date==db_expiry_date:
        # not interesting
        return None

    # Different!
    contract_object.contract_date.expiry_date = ib_expiry_date.as_tuple()
    data.mongo_contract_data.add_contract_data(contract_object, ignore_duplication=True)

    log.msg("Updated expiry of contract %s to %s" % (str(contract_object), str(ib_expiry_date)),
            contract_date = contract_object.date)

    return None

