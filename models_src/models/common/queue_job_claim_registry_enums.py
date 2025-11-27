from enum import Enum


class QRegistryStat(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    RETRY = "retry"
    FAILED = "failed"
    COMPLETED = "completed"
