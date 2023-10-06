import pytest
from syslogging.logger import *


class TestLogging:
    def test_name(self, caplog):
        logger = get_logger("my_type")
        assert logger.name == "my_type"
        assert logger.getEffectiveLevel() == logging.DEBUG

        logger.info("foo %s", "bar")
        assert caplog.record_tuples == [("my_type", logging.INFO, "foo bar")]

    def test_attributes_good(self, caplog):
        logger = get_logger("my_type", {"stage": "bar"})
        logger.warning("foo %s", "bar")
        assert caplog.record_tuples == [
            ("my_type", logging.WARNING, "{'stage': 'bar'} foo bar")
        ]

    def test_attributes_bad(self):
        with pytest.raises(Exception):
            get_logger("my_type", {"foo": "bar"})

    def test_no_name_no_attributes(self, caplog):
        logger = get_logger("")
        logger.warning("foo")
        assert caplog.record_tuples == [("root", logging.WARNING, "foo")]

    def test_attributes_clear(self, caplog):
        clear = get_logger("Clear", {"stage": "first", "type": "one"})
        clear.info("Clearing attributes", method="clear")
        assert caplog.record_tuples == [("Clear", logging.INFO, "Clearing attributes")]
        caplog.clear()
        clear.info("Clearing attributes", method="clear", stage="second")
        assert caplog.record_tuples == [
            ("Clear", logging.INFO, "{'stage': 'second'} Clearing attributes")
        ]

    def test_attributes_preserve(self, caplog):
        preserve = get_logger("Preserve", {"stage": "first"})
        preserve.info(
            "Preserving attributes", method="preserve", type="one", stage="second"
        )
        assert caplog.record_tuples == [
            (
                "Preserve",
                logging.INFO,
                "{'type': 'one', 'stage': 'first'} Preserving attributes",
            )
        ]

    def test_attributes_overwrite(self, caplog):
        overwrite = get_logger("Overwrite", {"stage": "first"})
        overwrite.info(
            "Overwriting attributes", method="overwrite", type="one", stage="second"
        )
        assert caplog.record_tuples == [
            (
                "Overwrite",
                logging.INFO,
                "{'stage': 'second', 'type': 'one'} Overwriting attributes",
            )
        ]

    def test_attributes_temp(self, caplog):
        temp = get_logger("temp", {"stage": "first"})
        temp.info("setting temp 'type' attribute", method="temp", type="one")
        assert caplog.record_tuples[0] == (
            "temp",
            logging.INFO,
            "{'stage': 'first', 'type': 'one'} setting temp 'type' attribute",
        )
        temp.info("no type attribute")
        assert caplog.record_tuples[1] == (
            "temp",
            logging.INFO,
            "{'stage': 'first'} no type attribute",
        )

    def test_setup(self):
        logger = get_logger("my_type", {"stage": "bar"})
        logger = logger.setup(stage="left")
        assert logger.name == "my_type"
        assert logger.extra["stage"] == "left"

        no_attrs = get_logger("no_attrs")
        no_attrs = no_attrs.setup(instrument_code="XYZ")
        assert no_attrs.extra["instrument_code"] == "XYZ"

    def test_setup_bad(self):
        logger = get_logger("my_type", {"stage": "bar"})
        with pytest.raises(Exception):
            logger.setup(foo="bar")
