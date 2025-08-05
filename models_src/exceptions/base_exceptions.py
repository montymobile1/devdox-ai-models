import logging
from typing import Any, Dict, Optional


class DevDoxModelsException(Exception):

    def __init__(
        self,
        *,
        user_message: str,
        log_message: Optional[str] = None,
        error_type: Optional[str] = None,
        public_context: Optional[Dict[str, Any]] = None,
        internal_context: Optional[Dict[str, Any]] = None,
        log_level: Optional[int] = None
    ):
        """
        Args:
                user_message: Safe, generic message returned to the user.
                public_context: Optional context to return in the API response (e.g., {"quota": "exceeded"}).

                log_message: Detailed internal message for logs/debugging.
                internal_context: Optional context to include in logs only (e.g., {"repo_id": 123}).

                error_type: Optional machine-readable code.
                log_level: Specifies the log level for this instance leveraging the python logging module int representation
        """
        super().__init__(user_message)

        self.user_message = user_message
        self.log_message = log_message or user_message
        self.error_type = error_type or self.__class__.__name__.upper()
        self.public_context = public_context or {}
        self.internal_context = internal_context or {}

        if not log_level:
            log_level = logging.WARNING

        self.log_level = logging.getLevelName(log_level).lower()

    def __str__(self):
        return f"[{self.error_type}] {self.user_message}"
