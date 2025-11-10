from models_src.exceptions.base_exceptions import DevDoxModelsException
from models_src.exceptions.exception_constants import JOB_ALREADY_CLAIMED


class JobAlreadyClaimed(DevDoxModelsException):
	
	def __init__(self, reason=None, log_message=None, log_level=None):
		
		if not reason or not reason.strip():
			reason = JOB_ALREADY_CLAIMED
		
		super().__init__(
			user_message=reason, log_message=log_message, log_level=log_level
		)