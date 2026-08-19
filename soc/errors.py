"""Public, structured error hierarchy for predictable SOC failures."""


class SOCError(Exception):
    code = "soc_error"

    def __init__(self, message, *, details=None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_dict(self):
        result = {"code": self.code, "message": self.message}
        if self.details:
            result["details"] = self.details
        return result


class ValidationError(SOCError, ValueError):
    code = "validation_error"


class QueryError(SOCError, ValueError):
    code = "query_error"


class AlertTransitionError(ValidationError):
    code = "alert_transition_error"


class StorageError(SOCError):
    code = "storage_error"


class StorageReadError(StorageError):
    code = "storage_read_error"


class StorageWriteError(StorageError):
    code = "storage_write_error"
