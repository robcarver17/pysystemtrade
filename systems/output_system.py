from systems.basesystem import System
from syslogdiag.log import logtoscreen


class outputSystem(System):
    """
    An output system is similar to a simulation system, except it has an additional output stage; and a name used for log identifier

    This is the pattern for production systems that will always have some output
    """

    def __init__(
        self,
        stage_list,
        data,
        output,
        system_name="output_system",
        config=None,
        logging_function=logtoscreen,
    ):
        """
        Create a production system instance

        :param stage_list: list of objects type stage
        :param data: an input data function
        :param output: an output function
        :param system_name: name of the system, used for logging
        :param config: a configuration object
        :param logging_function: function used for logging

        >>> from systems.stage import SystemStage
        >>> stage=SystemStage()
        >>> from sysdata.csv.csv_sim_futures_data import csvFuturesSimData
        >>> data=csvFuturesSimData()
        using /home/rob/workspace3/pysystemtrade/data/futures/legacycsv
        >>> outputSystem([stage], data, data, "test_system")
        System test_system with .config, .data, and .stages: unnamed

        """

        super().__init__(
            stage_list, data, config=config, log=logging_function(system_name)
        )

        # additional output stage
        setattr(self, "output", output)
        self.output._system_init(self)

        self.name = system_name


if __name__ == "__main__":
    import doctest

    doctest.testmod()
