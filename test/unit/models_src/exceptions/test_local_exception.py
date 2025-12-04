import logging

import pytest

from models_src.exceptions.exception_constants import JOB_ALREADY_CLAIMED
from models_src.exceptions.local_exception import JobAlreadyClaimed


class TestJobAlreadyClaimed:
	
	
	def test_raise_exception(self):
		
		reason = "xyz"
		log_message= "this is a log message"
		log_level = logging.ERROR
		
		exp = JobAlreadyClaimed(
			reason=reason,
			log_message=log_message,
			log_level=log_level
		)
		
		with pytest.raises(JobAlreadyClaimed) as p:
			raise exp
		
		assert p.value.user_message == reason
		assert p.value.log_message == log_message
		assert p.value.log_level.lower() == logging.getLevelName(log_level).lower()
	
	@pytest.mark.parametrize(
		"reason",
		[
			"",
			" ",
			None,
		],
		ids=["Empty reason", "Blank reason", "None reason"]
	)
	def test_raise_exception_default_reason(self, reason):
		
		log_message= "this is a log message"
		log_level = logging.ERROR
		
		exp = JobAlreadyClaimed(
			reason=reason,
			log_message=log_message,
			log_level=log_level
		)
		
		with pytest.raises(JobAlreadyClaimed) as p:
			raise exp
		
		assert p.value.user_message == JOB_ALREADY_CLAIMED
		assert p.value.log_message == log_message
		assert p.value.log_level.lower() == logging.getLevelName(log_level).lower()