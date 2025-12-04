from models_src.models.beanie_odm.queue_job_claim_registry_document import QueueProcessingRegistry


def test_document_str():
	rp = QueueProcessingRegistry.model_construct(
		message_id="message_id",
		status="status",
		queue_name="queue_name",
	)
	
	assert str(rp) == f"QueueProcessingRegistry(message_id={rp.message_id}, status={rp.status}, queue={rp.queue_name})"