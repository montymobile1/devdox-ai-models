import datetime
import uuid
from dataclasses import dataclass, field
from typing import Optional

from tortoise import fields, Model

from models_src.dto.utils import TortoiseModelMapper


class TestTortoiseModelMapper:
	
	mapper = TortoiseModelMapper
	
	class UserModel(Model):
		id = fields.UUIDField(primary_key=True, default=uuid.uuid4)
		user_id = fields.CharField(max_length=255, description="User ID")
		
		first_name = fields.CharField(max_length=255, description="First name of user")
		last_name = fields.CharField(max_length=255, description="Last name of user")
		email = fields.CharField(max_length=255, description="Email of user")
		username = fields.CharField(
			default="",
			max_length=255,
			description="Username of user",
		)
		role = fields.CharField(max_length=255, description="Role name of user")
		active = fields.BooleanField(default=True)
		
		membership_level = fields.CharField(
			max_length=100, default="free", description="Default membership_level"
		)
		token_limit = fields.IntField(
			default=0, description="Number of token of each month"
		)
		token_used = fields.IntField(default=0, description="Number of tokens used")
		
		# Timestamps
		created_at = fields.DatetimeField(
			auto_now_add=True, description="Record creation timestamp"
		)
		updated_at = fields.DatetimeField(
			auto_now=True, description="Record updated timestamp"
		)
		
		encryption_salt = fields.CharField(
			default="0", max_length=255, description="Encryption salt"
		)
		
		class Meta:
			table = "user"
			table_description = "User information from Clerk"
			indexes = [
				("user_id", "created_at"),
			]
		
		def __str__(self):
			return f"{self.first_name} {self.last_name} ({self.email})"
		
		def __repr__(self):
			return self.__str__()
	
	def test_map_model_to_dataclass_where_model_and_dto_have_equal_fields(self):
		
		model_id = uuid.uuid4()
		
		user_model_instance = self.UserModel(
			id=model_id,
			user_id="user_id",
			first_name="first_name",
			last_name="last_name",
			email="email",
			username="username",
			role="role",
			active=True,
			membership_level="membership_level",
			token_limit=1,
			token_used=1,
			created_at=datetime.datetime.now(datetime.UTC),
			updated_at=datetime.datetime.now(datetime.UTC),
			encryption_salt="encryption_salt"
		)
		
		@dataclass
		class UserResponseDTO:
			id: uuid.UUID
			user_id: str
			first_name: str
			last_name: str
			email: str
			username: str
			role: str
			active: bool
			membership_level: str
			token_limit: int
			token_used: int
			created_at: datetime.datetime
			updated_at: datetime.datetime
			encryption_salt: str

		mapped_class = self.mapper.map_model_to_dataclass(user_model_instance, UserResponseDTO)
		
		assert mapped_class.id == user_model_instance.id
		assert mapped_class.user_id == user_model_instance.user_id
		assert mapped_class.first_name == user_model_instance.first_name
		assert mapped_class.last_name == user_model_instance.last_name
		assert mapped_class.email == user_model_instance.email
		assert mapped_class.username == user_model_instance.username
		assert mapped_class.role == user_model_instance.role
		assert mapped_class.active == user_model_instance.active
		assert mapped_class.membership_level == user_model_instance.membership_level
		assert mapped_class.token_limit == user_model_instance.token_limit
		assert mapped_class.token_used == user_model_instance.token_used
		assert mapped_class.created_at == user_model_instance.created_at
		assert mapped_class.updated_at == user_model_instance.updated_at
		assert mapped_class.encryption_salt == user_model_instance.encryption_salt
	
	def test_map_model_to_dataclass_where_dto_has_less_fields_than_model(self):
		model_id = uuid.uuid4()
		
		user_model_instance = self.UserModel(
			id=model_id,
			user_id="user_id",
			first_name="first_name",
			last_name="last_name",
			email="email",
			username="username",
			role="role",
			active=True,
			membership_level="membership_level",
			token_limit=1,
			token_used=1,
			created_at=datetime.datetime.now(datetime.UTC),
			updated_at=datetime.datetime.now(datetime.UTC),
			encryption_salt="encryption_salt"
		)
		
		@dataclass
		class UserResponseDTO:
			id: uuid.UUID
			user_id: str
		
		mapped_class = self.mapper.map_model_to_dataclass(user_model_instance, UserResponseDTO)
		
		assert mapped_class.id == user_model_instance.id
		assert mapped_class.user_id == user_model_instance.user_id
	
	def test_map_model_to_dataclass_where_dto_has_extra_field_not_in_model(self):
		model_id = uuid.uuid4()
		
		user_model_instance = self.UserModel(
			id=model_id,
			user_id="user_id",
			first_name="first_name",
			last_name="last_name",
			email="email",
			username="username",
			role="role",
			active=True,
			membership_level="membership_level",
			token_limit=1,
			token_used=1,
			created_at=datetime.datetime.now(datetime.UTC),
			updated_at=datetime.datetime.now(datetime.UTC),
			encryption_salt="encryption_salt"
		)
		
		@dataclass
		class UserResponseDTO:
			id: uuid.UUID
			user_id: str
			extra_required_field: str = field(init=False)
			extra_optional_field: Optional[str] = field(init=False, default=None)
		
		mapped_class = self.mapper.map_model_to_dataclass(user_model_instance, UserResponseDTO)
		mapped_class.extra_required_field = "extra_required_field"
		
		assert mapped_class.id == user_model_instance.id
		assert mapped_class.user_id == user_model_instance.user_id
		assert mapped_class.extra_required_field == "extra_required_field"
		assert mapped_class.extra_optional_field is None
		