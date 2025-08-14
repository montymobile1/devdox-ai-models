import logging
from enum import Enum

from models_src.exceptions.base_exceptions import DevDoxModelsException
from models_src.exceptions.exception_constants import (
    LABEL_ALREADY_EXISTS_MESSAGE,
    LABEL_ALREADY_EXISTS_TITLE,
    MISSING_API_KEY_USER_ID_LOG_MESSAGE,
    MISSING_LABEL_ID_TITLE,
    MISSING_LABEL_LOG_MESSAGE,
    MISSING_USER_ID_LOG_MESSAGE,
    MISSING_USER_ID_TITLE,
    REPO_ALREADY_EXISTS_MESSAGE,
    REPO_ALREADY_EXISTS_TITLE,
    REPOSITORY_DOESNT_EXIST_MESSAGE,
    REPOSITORY_DOESNT_EXIST_TITLE,
)


def internal_error(
    log_message: str, error_type: str, log_level=logging.FATAL, **kwargs
):
    return DevDoxModelsException(
        user_message=log_message,
        log_message=log_message,
        error_type=error_type,
        log_level=log_level,
        **kwargs,
    )


class GitLabelErrors(Enum):
    MISSING_USER_ID = {
        "error_type": MISSING_USER_ID_TITLE,
        "log_message": MISSING_USER_ID_LOG_MESSAGE,
    }

    MISSING_LABEL = {
        "error_type": MISSING_LABEL_ID_TITLE,
        "log_message": MISSING_LABEL_LOG_MESSAGE,
    }

    GIT_LABEL_ALREADY_EXISTS = {
        "error_type": LABEL_ALREADY_EXISTS_TITLE,
        "log_message": LABEL_ALREADY_EXISTS_MESSAGE,
        "log_level": logging.ERROR,
    }


class RepoErrors(Enum):
    REPOSITORY_DOESNT_EXIST = {
        "error_type": REPOSITORY_DOESNT_EXIST_TITLE,
        "log_message": REPOSITORY_DOESNT_EXIST_MESSAGE,
    }

    REPOSITORY_ALREADY_EXIST = {
        "error_type": REPO_ALREADY_EXISTS_TITLE,
        "log_message": REPO_ALREADY_EXISTS_MESSAGE,
        "log_level": logging.ERROR,
    }


class ApiKeysErrors(Enum):
    MISSING_USER_ID = {
        "error_type": MISSING_USER_ID_TITLE,
        "log_message": MISSING_API_KEY_USER_ID_LOG_MESSAGE,
    }
