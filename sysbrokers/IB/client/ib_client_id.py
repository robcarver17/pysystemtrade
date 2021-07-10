from syscore.objects import arg_not_supplied

from syslogdiag.log_to_screen import logtoscreen

from sysbrokers.IB.ib_connection_defaults import ib_defaults
from sysdata.production.broker_client_id import brokerClientIdData

class ibBrokerClientIdData(brokerClientIdData):
    """
    Read and write data class to get next used client id
    """

    def __init__(
        self,
            idoffset = arg_not_supplied,
        log=logtoscreen("brokerClientIdTracker"),
    ):
        if idoffset is arg_not_supplied:
            _notused_ipaddress, _notused_port, _notused_readonly, idoffset = ib_defaults()

        super().__init__(log=log, idoffset=idoffset)

    def __repr__(self):
        return "Tracking IB client IDs"

