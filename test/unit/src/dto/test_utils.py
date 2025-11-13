import datetime
import uuid
from dataclasses import dataclass, field
from typing import Optional

import pymongo
import pytest
from beanie import Document, Indexed
from pydantic import Field
from tortoise import fields, Model

from models_src.dto.utils import BeanieModelMapper, DataclassMapper, TortoiseModelMapper

class TestDataclassMapper:
    mapper = DataclassMapper
    
    @pytest.mark.parametrize(
        ("source", "target_cls"),
        [
            (None, "SOME VALID DATACLASS"),
            ("SOME VALID DATACLASS", None),
        ],
        ids=["None source dataclass", "None target_cls dataclass"]
    )
    def test_map_dataclass_to_dataclass_validations(self, source, target_cls):

        res = self.mapper.map_dataclass_to_dataclass(
            source=source, target_cls=target_cls
        )
        
        assert not res
    
    def test_map_dataclass_to_dataclass_have_equal_fields(self):
        
        @dataclass
        class CS1:
            first_name: str
            last_name: str
        
        @dataclass
        class CS2:
            first_name: str
            last_name: str
        
        cs1 = CS1(
            first_name="Mohammad",
            last_name="Jaafar"
        )
        
        mapped_class = self.mapper.map_dataclass_to_dataclass(
            cs1, CS2
        )
        
        assert isinstance(mapped_class, CS2)
        assert mapped_class.first_name == cs1.first_name
        assert mapped_class.last_name == cs1.last_name
    
    
    def test_map_dataclass_to_dataclass_where_dataclass_has_less_fields_than_other(self):
        
        @dataclass
        class CS1:
            first_name: str
            last_name: str
            email: str
        
        @dataclass
        class CS2:
            first_name: str
            last_name: str
        
        cs1 = CS1(
            first_name="Mohammad",
            last_name="Jaafar",
            email="moo"
        )
        
        mapped_class = self.mapper.map_dataclass_to_dataclass(
            cs1, CS2
        )
        
        assert isinstance(mapped_class, CS2)
        assert mapped_class.first_name == cs1.first_name
        assert mapped_class.last_name == cs1.last_name

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
    
    @pytest.mark.parametrize(
        ("sources", "target_cls"),
        [
            (None, "VALID"),
            ([], "VALID"),
            ("VALID", None),
        ],
        ids=["None source", "Empty Source", "None target_cls"]
    )
    def test_map_models_to_dataclasses_list_validations(self, sources, target_cls):
        
        mapped_class = self.mapper.map_models_to_dataclasses_list(
            sources=sources, target_cls=target_cls
        )
        
        assert isinstance(mapped_class, list)
        assert len(mapped_class) == 0
        
    
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
            encryption_salt="encryption_salt",
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

        mapped_class = self.mapper.map_model_to_dataclass(
            user_model_instance, UserResponseDTO
        )

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
            encryption_salt="encryption_salt",
        )

        @dataclass
        class UserResponseDTO:
            id: uuid.UUID
            user_id: str

        mapped_class = self.mapper.map_model_to_dataclass(
            user_model_instance, UserResponseDTO
        )

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
            encryption_salt="encryption_salt",
        )

        @dataclass
        class UserResponseDTO:
            id: uuid.UUID
            user_id: str
            extra_required_field: str = field(init=False)
            extra_optional_field: Optional[str] = field(init=False, default=None)

        mapped_class = self.mapper.map_model_to_dataclass(
            user_model_instance, UserResponseDTO
        )
        mapped_class.extra_required_field = "extra_required_field"

        assert mapped_class.id == user_model_instance.id
        assert mapped_class.user_id == user_model_instance.user_id
        assert mapped_class.extra_required_field == "extra_required_field"
        assert mapped_class.extra_optional_field is None

class TestBeanieModelMapper:

    mapper = BeanieModelMapper
    
    class UserDocument(Document):
        """
        User document for storing user information from Clerk.
        """
        
        id: uuid.UUID = Field(default_factory=uuid.uuid4)
        
        user_id: Indexed(str) = Field(
            ...,
            max_length=255,
            description="User ID (from Clerk)",
        )
        
        first_name: str = Field(..., max_length=255, description="First name of user")
        last_name: str = Field(..., max_length=255, description="Last name of user")
        email: str = Field(..., max_length=255, description="Email of user")
        username: str = Field(default="", max_length=255, description="Username of user")
        role: str = Field(..., max_length=255, description="Role name of user")
        active: bool = Field(default=True)
        
        membership_level: str = Field(
            default="free", max_length=100, description="Default membership level"
        )
        token_limit: int = Field(default=0, description="Monthly token quota")
        token_used: int = Field(default=0, description="Tokens used this month")
        
        encryption_salt: str = Field(default="0", max_length=255, description="Encryption salt")
        
        class Settings:
            name = "user"
            
            description = "User information from Clerk"
            
            indexes = [
                pymongo.IndexModel(
                    [("user_id", pymongo.ASCENDING), ("created_at", pymongo.DESCENDING)]
                )
            ]
        
        def __str__(self) -> str:
            return f"{self.first_name} {self.last_name} ({self.email})"
        
        def __repr__(self) -> str:
            return self.__str__()
    
    @pytest.mark.parametrize(
        ("source", "target_cls"),
        [
            (None, "VALID"),
            ("VALID", None),
        ],
        ids=["None source", "None target_cls"]
    )
    def test_map_document_to_dataclass_validations(self, source, target_cls):
        
        mapped_class = self.mapper.map_document_to_dataclass(
            source=source, target_cls=target_cls
        )
        
        assert not mapped_class
    
    @pytest.mark.parametrize(
        ("sources", "target_cls"),
        [
            (None, "VALID"),
            ([], "VALID"),
            ("VALID", None),
        ],
        ids=["None source", "Empty Sources", "None target_cls"]
    )
    def test_map_documents_to_dataclasses_list_validations(self, sources, target_cls):
        
        mapped_class = self.mapper.map_documents_to_dataclasses_list(
            sources=sources, target_cls=target_cls
        )
        
        assert isinstance(mapped_class, list)
        assert len(mapped_class) == 0
    
    def test_map_document_to_dataclass_where_document_and_dto_have_equal_fields(self):

        model_id = uuid.uuid4()

        user_document_instance = self.UserDocument.model_construct(
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
            encryption_salt="encryption_salt",
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
            encryption_salt: str

        mapped_class = self.mapper.map_document_to_dataclass(
            user_document_instance, UserResponseDTO
        )

        assert mapped_class.id == user_document_instance.id
        assert mapped_class.user_id == user_document_instance.user_id
        assert mapped_class.first_name == user_document_instance.first_name
        assert mapped_class.last_name == user_document_instance.last_name
        assert mapped_class.email == user_document_instance.email
        assert mapped_class.username == user_document_instance.username
        assert mapped_class.role == user_document_instance.role
        assert mapped_class.active == user_document_instance.active
        assert mapped_class.membership_level == user_document_instance.membership_level
        assert mapped_class.token_limit == user_document_instance.token_limit
        assert mapped_class.token_used == user_document_instance.token_used
        assert mapped_class.encryption_salt == user_document_instance.encryption_salt

    def test_map_document_to_dataclass_where_dto_has_less_fields_than_document(self):
        model_id = uuid.uuid4()

        user_document_instance = self.UserDocument.model_construct(
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
            encryption_salt="encryption_salt",
        )

        @dataclass
        class UserResponseDTO:
            id: uuid.UUID
            user_id: str

        mapped_class = self.mapper.map_document_to_dataclass(
            user_document_instance, UserResponseDTO
        )

        assert mapped_class.id == user_document_instance.id
        assert mapped_class.user_id == user_document_instance.user_id

    def test_map_document_to_dataclass_where_dto_has_extra_field_not_in_document(self):
        model_id = uuid.uuid4()

        user_document_instance = self.UserDocument.model_construct(
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
            encryption_salt="encryption_salt",
        )

        @dataclass
        class UserResponseDTO:
            id: uuid.UUID
            user_id: str
            extra_required_field: str = field(init=False)
            extra_optional_field: Optional[str] = field(init=False, default=None)

        mapped_class = self.mapper.map_document_to_dataclass(
            user_document_instance, UserResponseDTO
        )
        mapped_class.extra_required_field = "extra_required_field"

        assert mapped_class.id == user_document_instance.id
        assert mapped_class.user_id == user_document_instance.user_id
        assert mapped_class.extra_required_field == "extra_required_field"
        assert mapped_class.extra_optional_field is None
    
    def test_map_documents_to_dataclasses_list_where_document_and_dto_have_equal_fields(self):
        
        total_documents_to_generate = 3
        
        user_document_instances:dict = {}
        
        for i in range(total_documents_to_generate):
            document_id = uuid.uuid4()
            user_document_instances[str(document_id)] = self.UserDocument.model_construct(
                    id=document_id,
                    user_id=f"user_id_{i}",
                    first_name=f"first_name_{i}",
                    last_name=f"last_name_{i}",
                    email=f"email_{i}",
                    username=f"username_{i}",
                    role=f"role_{i}",
                    active=True,
                    membership_level=f"membership_level_{i}",
                    token_limit=1,
                    token_used=1,
                    encryption_salt=f"encryption_salt_{i}",
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
            encryption_salt: str
        
        mapped_classes = self.mapper.map_documents_to_dataclasses_list(
            list(user_document_instances.values()), UserResponseDTO
        )
        
        for mapped_class in mapped_classes:
            
            user_document_instance = user_document_instances.get(str(mapped_class.id))
            
            assert user_document_instance
            assert mapped_class.id == user_document_instance.id
            assert mapped_class.user_id == user_document_instance.user_id
            assert mapped_class.first_name == user_document_instance.first_name
            assert mapped_class.last_name == user_document_instance.last_name
            assert mapped_class.email == user_document_instance.email
            assert mapped_class.username == user_document_instance.username
            assert mapped_class.role == user_document_instance.role
            assert mapped_class.active == user_document_instance.active
            assert mapped_class.membership_level == user_document_instance.membership_level
            assert mapped_class.token_limit == user_document_instance.token_limit
            assert mapped_class.token_used == user_document_instance.token_used
            assert mapped_class.encryption_salt == user_document_instance.encryption_salt
    
    def test_map_documents_to_dataclasses_list_where_dto_has_less_fields_than_document(self):
        total_documents_to_generate = 3
        
        user_document_instances:dict = {}
        
        for i in range(total_documents_to_generate):
            document_id = uuid.uuid4()
            user_document_instances[str(document_id)] = self.UserDocument.model_construct(
                id=document_id,
                user_id=f"user_id_{i}",
                first_name=f"first_name_{i}",
                last_name=f"last_name_{i}",
                email=f"email_{i}",
                username=f"username_{i}",
                role=f"role_{i}",
                active=True,
                membership_level=f"membership_level_{i}",
                token_limit=1,
                token_used=1,
                encryption_salt=f"encryption_salt_{i}",
            )
        
        @dataclass
        class UserResponseDTO:
            id: uuid.UUID
            user_id: str
        
        mapped_classes = self.mapper.map_documents_to_dataclasses_list(
            list(user_document_instances.values()), UserResponseDTO
        )
        
        for mapped_class in mapped_classes:
            
            user_document_instance = user_document_instances.get(str(mapped_class.id))
            
            assert user_document_instance
            assert mapped_class.id == user_document_instance.id
            assert mapped_class.user_id == user_document_instance.user_id
    
    def test_map_documents_to_dataclasses_list_where_dto_has_extra_field_not_in_document(self):
        total_documents_to_generate = 3
        
        user_document_instances:dict = {}
        
        for i in range(total_documents_to_generate):
            document_id = uuid.uuid4()
            user_document_instances[str(document_id)] = self.UserDocument.model_construct(
                id=document_id,
                user_id=f"user_id_{i}",
                first_name=f"first_name_{i}",
                last_name=f"last_name_{i}",
                email=f"email_{i}",
                username=f"username_{i}",
                role=f"role_{i}",
                active=True,
                membership_level=f"membership_level_{i}",
                token_limit=1,
                token_used=1,
                encryption_salt=f"encryption_salt_{i}",
            )
        
        @dataclass
        class UserResponseDTO:
            id: uuid.UUID
            user_id: str
            extra_required_field: str = field(init=False)
            extra_optional_field: Optional[str] = field(init=False, default=None)
        
        mapped_classes = self.mapper.map_documents_to_dataclasses_list(
            list(user_document_instances.values()), UserResponseDTO
        )
        
        for mapped_class in mapped_classes:
            
            user_document_instance = user_document_instances.get(str(mapped_class.id))
            
            mapped_class.extra_required_field = "extra_required_field"
            
            assert mapped_class.id == user_document_instance.id
            assert mapped_class.user_id == user_document_instance.user_id
            assert mapped_class.extra_required_field == "extra_required_field"
            assert mapped_class.extra_optional_field is None