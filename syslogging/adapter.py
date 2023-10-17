import logging
import logging.config
import warnings

from syslogdiag.pst_logger import *


class DynamicAttributeLogger(logging.LoggerAdapter):

    """
    # TODO futures_contract.specific_log
    # TODO log_with_attributes

    """

    def __init__(self, logger, attributes) -> None:
        self._check_attributes(attributes)
        super().__init__(logger, attributes)

    def process(self, msg, kwargs):
        attrs = dict()
        new_kwargs = dict()

        method = kwargs.pop("method", "overwrite")
        if method not in ["clear", "preserve", "overwrite", "temp"]:
            raise ValueError(f"Invalid value for 'method': {method}")

        for k, v in kwargs.items():
            if k in ALLOWED_LOG_ATTRIBUTES:
                attrs[k] = v
            else:
                new_kwargs[k] = v

        """
        Four possible ways to deal with attributes
        1. temp: passed values overwrite existing for one message, then discarded
        2. clear:  clear existing, use passed values
        3. preserve: merge with existing values preserved
        4. overwrite: merge with existing values overwritten
        """
        if method == "temp":
            if self.extra:
                return "%s %s" % ({**self.extra, **attrs}, msg), new_kwargs
            else:
                return "%s %s" % (attrs, msg), new_kwargs
        else:
            merged = self._merge_attributes(method, attrs)
            new_kwargs["extra"] = merged
            self.extra = merged

            if self.extra:
                return "%s %s" % (self.extra, msg), new_kwargs
            else:
                return "%s" % msg, new_kwargs

    def _merge_attributes(self, method, attributes):
        if not self.extra or method == "clear":
            merged = attributes
        elif method == "preserve":
            merged = {**attributes, **self.extra}
        else:
            merged = {**self.extra, **attributes}

        return merged

    def setup(self, **kwargs):
        # Create a copy of me with different attributes
        warnings.warn(
            "The 'setup' function is deprecated; instead, "
            "update attributes with method=clear/preserve/overwrite/temp",
            DeprecationWarning,
            2,
        )
        attributes = {**kwargs}
        self._check_attributes(attributes)
        return DynamicAttributeLogger(logging.getLogger(self.name), attributes)

    def _check_attributes(self, attributes: dict):
        if attributes:
            bad_attributes = get_list_of_disallowed_attributes(attributes)
            if len(bad_attributes) > 0:
                raise Exception(
                    "Attributes %s not allowed in log" % str(bad_attributes)
                )
