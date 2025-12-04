from models_src.exceptions import exception_constants
from models_src.exceptions.base_exceptions import DevDoxModelsException

class JobAlreadyClaimed(DevDoxModelsException):
	
	def __init__(self, reason=None, log_message=None, log_level=None):
		
		if not reason or not reason.strip():
			reason = exception_constants.JOB_ALREADY_CLAIMED
		
		super().__init__(
			user_message=reason, log_message=log_message, log_level=log_level
		)

class InMemoryNotFound(DevDoxModelsException):
	"""
	Used to simulate Beanie ODM `DocumentNotFound` and Tortoise ORM `DoesNotExist`
	"""
	def __init__(self, reason=None):
		
		if not reason or not reason.strip():
			reason = exception_constants.RECORD_NOT_FOUND
		
		super().__init__(
			user_message=reason
		)

class InMemoryDuplicate(DevDoxModelsException):
	"""
	Used to simulate Beanie ODM `DuplicateKeyError` and Tortoise ORM `IntegrityError`
	"""
	def __init__(self, reason=None):
		super().__init__(
			user_message=reason
		)