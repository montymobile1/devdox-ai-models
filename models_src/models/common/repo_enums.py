from enum import StrEnum


class QueueJobType(StrEnum):
    ANALYZE = "analyze"
    REANALYZE = "reanalyze"
    PROCESS = "process"

class StatusTypes(StrEnum):
    PENDING = "pending"
    ANALYSIS_PENDING = "analysis pending"
    REANALYSIS_PENDING = "re-analyse pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"