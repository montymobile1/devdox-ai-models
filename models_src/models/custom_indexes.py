"""
This module includes all the Partial indexes that need to be created, but since tortoise ORM does
not support Partial creation, we have to put them here and use them in a central location
"""
from models_src.models import queue_processing_registry_one_claim_unique, QueueProcessingRegistry

QUEUE_PROCESSING_REGISTRY_ONE_CLAIM_UNIQUE_INDEX = f"""
DROP INDEX IF EXISTS {queue_processing_registry_one_claim_unique};

CREATE UNIQUE INDEX IF NOT EXISTS {queue_processing_registry_one_claim_unique}
ON {QueueProcessingRegistry.Meta.table} (message_id)
WHERE status IN ('pending', 'in_progress');
"""

CUSTOM_INDEXES = {
    QueueProcessingRegistry.Meta.table: [QUEUE_PROCESSING_REGISTRY_ONE_CLAIM_UNIQUE_INDEX]
}

