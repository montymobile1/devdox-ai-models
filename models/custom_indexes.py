"""
This module includes all the Partial indexes that need to be created, but since tortoise ORM does
not support Partial creation, we have to put them here and use them in a central location
"""
import models

QUEUE_PROCESSING_REGISTRY_ONE_CLAIM_UNIQUE_INDEX = f"""
DROP INDEX IF EXISTS {models.queue_processing_registry_one_claim_unique};

CREATE UNIQUE INDEX IF NOT EXISTS {models.queue_processing_registry_one_claim_unique}
ON {models.QueueProcessingRegistry.Meta.table} (message_id)
WHERE status IN ('pending', 'in_progress');
"""

CUSTOM_INDEXES = {
    models.QueueProcessingRegistry.Meta.table: [QUEUE_PROCESSING_REGISTRY_ONE_CLAIM_UNIQUE_INDEX]
}

