import logging
import logging.config
import warnings

from syslogdiag.pst_logger import *


class DynamicAttributeLogger(logging.LoggerAdapter):

    """
    # TODO futures_contract.specific_log
    # TODO data_blob.update_log
    # TODO data.update_log(contract_object.specific_log(data.log))
    # TODO data_blob._get_specific_logger
    # TODO log_with_attributes

    """

    def __init__(self, logger, attributes) -> None:
        self._check_attributes(attributes)
        super().__init__(logger, attributes)

    def process(self, msg, kwargs):
        attrs = dict()
        new_kwargs = dict()

        method = kwargs.pop("method", "overwrite")
        if method not in ["clear", "preserve", "overwrite"]:
            raise ValueError(f"Invalid value for 'method': {method}")

        for k, v in kwargs.items():
            if k in ALLOWED_LOG_ATTRIBUTES:
                attrs[k] = v
            else:
                new_kwargs[k] = v

        merged = self._merge_attributes(method, attrs)
        new_kwargs["extra"] = merged
        self.extra = merged

        if self.extra:
            return "%s %s" % (self.extra, msg), new_kwargs
        else:
            return "%s" % msg, new_kwargs

    def _merge_attributes(self, method, attributes):
        """
        Three possible ways to deal with attributes
        1. clear:  clear existing, use passed values
        2. preserve: merge with existing values preserved
        3. overwrite: merge with existing values overwritten
        """
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
            "update attributes with method=clear/preserve/overwrite",
            DeprecationWarning,
            2,
        )
        attributes = {**kwargs}
        self._check_attributes(attributes)
        return DynamicAttributeLogger(logging.getLogger(self.name), attributes)

    def label(self, **kwargs):
        # permanently add new attributes to me
        warnings.warn(
            "The 'label' function is deprecated; instead, "
            "update attributes with method=clear/preserve/overwrite",
            DeprecationWarning,
            2,
        )
        if not self.extra:
            attributes = {**kwargs}
        else:
            attributes = {**self.extra, **kwargs}
        self._check_attributes(attributes)
        self.extra = attributes

    def setup_empty_except_keep_type(self):
        warnings.warn(
            "The 'setup_empty_except_keep_type' function is deprecated; instead, "
            "update attributes with method=clear/preserve/overwrite",
            DeprecationWarning,
            2,
        )
        if self.extra and TYPE_LOG_LABEL in self.extra:
            attributes = {TYPE_LOG_LABEL: self.extra[TYPE_LOG_LABEL]}
        else:
            attributes = {}
        return DynamicAttributeLogger(logging.getLogger(self.name), attributes)

    def _check_attributes(self, attributes: dict):
        if attributes:
            bad_attributes = get_list_of_disallowed_attributes(attributes)
            if len(bad_attributes) > 0:
                raise Exception(
                    "Attributes %s not allowed in log" % str(bad_attributes)
                )


class pst_logger(DynamicAttributeLogger):
    pass
