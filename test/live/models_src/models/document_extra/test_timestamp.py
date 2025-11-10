import datetime
import uuid
from typing import Optional

import pytest
from beanie import Document
from beanie.odm.actions import before_event, EventTypes
from beanie.odm.operators.update.general import Set
from pydantic import Field

from models_src.db_inits.beanie_init import init_via_uri
from models_src.models.document_extra.timestamp import TimestampAuditMixin

MONGO_URI = "mongodb://localhost:27017/devdox"


class SadLonelyDocument(TimestampAuditMixin, Document):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    description: str = Field(..., description="Just something to descripe the auditing stuff")
    operation_name: str = Field(..., description="The name of the CRUD operation")
    sad_field: Optional[int] = Field(default=0, description="A sad field to test updates on")
    
    class Settings:
        name = "sad_lonely_document"
        use_state_management = True
        state_management_save_previous = True
    
    @before_event(EventTypes.INSERT)
    def print_insert(self):
        print(f"Beanie Tracking for {self.description} operation Entered {EventTypes.INSERT.value}")
    
    @before_event(EventTypes.SAVE)
    def print_save(self):
        print(f"Beanie Tracking for {self.description} Entered {EventTypes.SAVE.value}")
    
    @before_event(EventTypes.SAVE_CHANGES)
    def print_save_changes(self):
        print(f"Beanie Tracking for {self.description} Entered {EventTypes.SAVE_CHANGES.value}")
    
    @before_event(EventTypes.REPLACE)
    def print_replace(self):
        print(f"Beanie Tracking for {self.description} Entered {EventTypes.REPLACE.value}")
    
    @before_event(EventTypes.UPDATE)
    def print_update(self):
        print(f"Beanie Tracking for {self.description} Entered {EventTypes.UPDATE.value}")


document_list_1 = [SadLonelyDocument]


class TestVanillaOnSave:
    
    @pytest.mark.asyncio
    @pytest.mark.skip("Not going to use `.save()` to save new docs, cause it does upsert and ruins TimeMixin")
    async def test_timestamp_with_save(self):
        
        # ARRANGE
        client, db = await init_via_uri(MONGO_URI, documents_list=document_list_1)
        
        try:
            
            for name in await db.list_collection_names():
                await db[name].delete_many({})
            
            # ARRANGE
            
            doc_with_default_timestamps_id = uuid.uuid4()
            doc_with_custom_created_at_timestamp_id = uuid.uuid4()
            doc_with_custom_updated_at_timestamp_id = uuid.uuid4()
            
            start_of_day = datetime.datetime.combine(datetime.datetime.now(tz=datetime.timezone.utc).date(), datetime.time.min)
            custom_created_at = start_of_day - datetime.timedelta(days=2)
            custom_updated_at = start_of_day - datetime.timedelta(days=1)
            
            doc_with_default_timestamps = SadLonelyDocument(
                id=doc_with_default_timestamps_id, operation_name=".save()", description="doc_with_default_timestamps"
            )
            
            doc_with_custom_created_at_timestamps = SadLonelyDocument(
                id=doc_with_custom_created_at_timestamp_id,
                created_at=custom_created_at,
                operation_name=".save()", description="doc_with_custom_created_at_timestamps"
            )
            
            doc_with_custom_update_at_timestamps = SadLonelyDocument(
                id=doc_with_custom_updated_at_timestamp_id,
                updated_at=custom_updated_at,
                operation_name=".save()", description="doc_with_custom_update_at_timestamps"
            )
            
            # ACT & ASSERT
            
            saved_doc_with_default_timestamps = await doc_with_default_timestamps.save()
            
            assert saved_doc_with_default_timestamps is not None
            assert saved_doc_with_default_timestamps.id == doc_with_default_timestamps_id
            assert saved_doc_with_default_timestamps.created_at == saved_doc_with_default_timestamps.updated_at
            assert saved_doc_with_default_timestamps.created_at.date() == datetime.datetime.now(datetime.timezone.utc).date()
            assert saved_doc_with_default_timestamps.updated_at.date() == datetime.datetime.now(datetime.timezone.utc).date()
            
            saved_doc_with_custom_created_at_timestamps = await doc_with_custom_created_at_timestamps.save()
            
            assert saved_doc_with_custom_created_at_timestamps is not None
            assert saved_doc_with_custom_created_at_timestamps.id == doc_with_custom_created_at_timestamp_id
            assert saved_doc_with_custom_created_at_timestamps.created_at == custom_created_at
            assert saved_doc_with_custom_created_at_timestamps.updated_at.date() == start_of_day.date()
            
            saved_doc_with_custom_updated_at_timestamps = await doc_with_custom_update_at_timestamps.save()
            
            assert saved_doc_with_custom_updated_at_timestamps is not None
            assert saved_doc_with_custom_updated_at_timestamps.id == doc_with_custom_updated_at_timestamp_id
            assert saved_doc_with_custom_updated_at_timestamps.created_at.date() == start_of_day.date()
            assert saved_doc_with_custom_updated_at_timestamps.updated_at == custom_updated_at
        
        finally:
            await client.drop_database(db.name)
            client.close()
    
    @pytest.mark.asyncio
    async def test_timestamp_with_insert(self):
        
        # ARRANGE
        client, db = await init_via_uri(MONGO_URI, documents_list=document_list_1)
        
        try:
            
            for name in await db.list_collection_names():
                await db[name].delete_many({})
            
            # ARRANGE
            
            doc_with_default_timestamps_id = uuid.uuid4()
            doc_with_custom_created_at_timestamp_id = uuid.uuid4()
            doc_with_custom_updated_at_timestamp_id = uuid.uuid4()
            
            start_of_day = datetime.datetime.combine(datetime.datetime.now(tz=datetime.timezone.utc).date(), datetime.time.min)
            custom_created_at = start_of_day - datetime.timedelta(days=2)
            custom_updated_at = start_of_day - datetime.timedelta(days=1)
            
            doc_with_default_timestamps = SadLonelyDocument(
                id=doc_with_default_timestamps_id, operation_name=".insert()", description="doc_with_default_timestamps"
            )
            
            doc_with_custom_created_at_timestamps = SadLonelyDocument(
                id=doc_with_custom_created_at_timestamp_id,
                created_at=custom_created_at, operation_name=".insert()", description="doc_with_custom_created_at_timestamps"
            )
            
            doc_with_custom_update_at_timestamps = SadLonelyDocument(
                id=doc_with_custom_updated_at_timestamp_id,
                updated_at=custom_updated_at, operation_name=".insert()", description="doc_with_custom_update_at_timestamps"
            )
            
            # ACT & ASSERT
            
            saved_doc_with_default_timestamps = await doc_with_default_timestamps.insert()
            
            assert saved_doc_with_default_timestamps is not None
            assert saved_doc_with_default_timestamps.id == doc_with_default_timestamps_id
            assert saved_doc_with_default_timestamps.created_at == saved_doc_with_default_timestamps.updated_at
            assert saved_doc_with_default_timestamps.created_at.date() == datetime.datetime.now(datetime.timezone.utc).date()
            assert saved_doc_with_default_timestamps.updated_at.date() == datetime.datetime.now(datetime.timezone.utc).date()
            
            saved_doc_with_custom_created_at_timestamps = await doc_with_custom_created_at_timestamps.insert()
            
            assert saved_doc_with_custom_created_at_timestamps is not None
            assert saved_doc_with_custom_created_at_timestamps.id == doc_with_custom_created_at_timestamp_id
            assert saved_doc_with_custom_created_at_timestamps.created_at == custom_created_at
            assert saved_doc_with_custom_created_at_timestamps.updated_at.date() == start_of_day.date()
            
            saved_doc_with_custom_updated_at_timestamps = await doc_with_custom_update_at_timestamps.insert()
            
            assert saved_doc_with_custom_updated_at_timestamps is not None
            assert saved_doc_with_custom_updated_at_timestamps.id == doc_with_custom_updated_at_timestamp_id
            assert saved_doc_with_custom_updated_at_timestamps.created_at.date() == start_of_day.date()
            assert saved_doc_with_custom_updated_at_timestamps.updated_at == custom_updated_at
        
        finally:
            await client.drop_database(db.name)
            await client.close()
    
    @pytest.mark.asyncio
    async def test_timestamp_with_create(self):
        
        # ARRANGE
        client, db = await init_via_uri(MONGO_URI, documents_list=document_list_1)
        
        try:
            
            for name in await db.list_collection_names():
                await db[name].delete_many({})
            
            # ARRANGE
            
            doc_with_default_timestamps_id = uuid.uuid4()
            doc_with_custom_created_at_timestamp_id = uuid.uuid4()
            doc_with_custom_updated_at_timestamp_id = uuid.uuid4()
            
            start_of_day = datetime.datetime.combine(datetime.datetime.now(tz=datetime.timezone.utc).date(), datetime.time.min)
            custom_created_at = start_of_day - datetime.timedelta(days=2)
            custom_updated_at = start_of_day - datetime.timedelta(days=1)
            
            doc_with_default_timestamps = SadLonelyDocument(
                id=doc_with_default_timestamps_id, operation_name=".create()", description="doc_with_default_timestamps"
            )
            
            doc_with_custom_created_at_timestamps = SadLonelyDocument(
                id=doc_with_custom_created_at_timestamp_id,
                created_at=custom_created_at, operation_name=".create()", description="doc_with_custom_created_at_timestamps"
            )
            
            doc_with_custom_update_at_timestamps = SadLonelyDocument(
                id=doc_with_custom_updated_at_timestamp_id,
                updated_at=custom_updated_at, operation_name=".create()", description="doc_with_custom_update_at_timestamps"
            )
            
            # ACT & ASSERT
            
            saved_doc_with_default_timestamps = await doc_with_default_timestamps.create()
            
            assert saved_doc_with_default_timestamps is not None
            assert saved_doc_with_default_timestamps.id == doc_with_default_timestamps_id
            assert saved_doc_with_default_timestamps.created_at == saved_doc_with_default_timestamps.updated_at
            assert saved_doc_with_default_timestamps.created_at.date() == datetime.datetime.now(datetime.timezone.utc).date()
            assert saved_doc_with_default_timestamps.updated_at.date() == datetime.datetime.now(datetime.timezone.utc).date()
            
            saved_doc_with_custom_created_at_timestamps = await doc_with_custom_created_at_timestamps.create()
            
            assert saved_doc_with_custom_created_at_timestamps is not None
            assert saved_doc_with_custom_created_at_timestamps.id == doc_with_custom_created_at_timestamp_id
            assert saved_doc_with_custom_created_at_timestamps.created_at == custom_created_at
            assert saved_doc_with_custom_created_at_timestamps.updated_at.date() == start_of_day.date()
            
            saved_doc_with_custom_updated_at_timestamps = await doc_with_custom_update_at_timestamps.create()
            
            assert saved_doc_with_custom_updated_at_timestamps is not None
            assert saved_doc_with_custom_updated_at_timestamps.id == doc_with_custom_updated_at_timestamp_id
            assert saved_doc_with_custom_updated_at_timestamps.created_at.date() == start_of_day.date()
            assert saved_doc_with_custom_updated_at_timestamps.updated_at == custom_updated_at
        
        finally:
            await client.drop_database(db.name)
            await client.close()
    
    @pytest.mark.asyncio
    async def test_timestamp_with_insert_one(self):
        
        # ARRANGE
        client, db = await init_via_uri(MONGO_URI, documents_list=document_list_1)
        
        try:
            
            for name in await db.list_collection_names():
                await db[name].delete_many({})
            
            # ARRANGE
            
            doc_with_default_timestamps_id = uuid.uuid4()
            doc_with_custom_created_at_timestamp_id = uuid.uuid4()
            doc_with_custom_updated_at_timestamp_id = uuid.uuid4()
            
            start_of_day = datetime.datetime.combine(datetime.datetime.now(tz=datetime.timezone.utc).date(), datetime.time.min)
            custom_created_at = start_of_day - datetime.timedelta(days=2)
            custom_updated_at = start_of_day - datetime.timedelta(days=1)
            
            doc_with_default_timestamps = SadLonelyDocument(
                id=doc_with_default_timestamps_id, operation_name=".insert_one()", description="doc_with_default_timestamps"
            )
            
            doc_with_custom_created_at_timestamps = SadLonelyDocument(
                id=doc_with_custom_created_at_timestamp_id,
                created_at=custom_created_at, operation_name=".insert_one()", description="doc_with_custom_created_at_timestamps"
            )
            
            doc_with_custom_update_at_timestamps = SadLonelyDocument(
                id=doc_with_custom_updated_at_timestamp_id,
                updated_at=custom_updated_at, operation_name=".insert_one()", description="doc_with_custom_update_at_timestamps"
            )
            
            # ACT & ASSERT
            
            saved_doc_with_default_timestamps = await SadLonelyDocument.insert_one(doc_with_default_timestamps)
            
            assert saved_doc_with_default_timestamps is not None
            assert saved_doc_with_default_timestamps.id == doc_with_default_timestamps_id
            assert saved_doc_with_default_timestamps.created_at == saved_doc_with_default_timestamps.updated_at
            assert saved_doc_with_default_timestamps.created_at.date() == datetime.datetime.now(datetime.timezone.utc).date()
            assert saved_doc_with_default_timestamps.updated_at.date() == datetime.datetime.now(datetime.timezone.utc).date()
            
            saved_doc_with_custom_created_at_timestamps = await SadLonelyDocument.insert_one(doc_with_custom_created_at_timestamps)
            
            assert saved_doc_with_custom_created_at_timestamps is not None
            assert saved_doc_with_custom_created_at_timestamps.id == doc_with_custom_created_at_timestamp_id
            assert saved_doc_with_custom_created_at_timestamps.created_at == custom_created_at
            assert saved_doc_with_custom_created_at_timestamps.updated_at.date() == start_of_day.date()
            
            saved_doc_with_custom_updated_at_timestamps = await SadLonelyDocument.insert_one(doc_with_custom_update_at_timestamps)
            
            assert saved_doc_with_custom_updated_at_timestamps is not None
            assert saved_doc_with_custom_updated_at_timestamps.id == doc_with_custom_updated_at_timestamp_id
            assert saved_doc_with_custom_updated_at_timestamps.created_at.date() == start_of_day.date()
            assert saved_doc_with_custom_updated_at_timestamps.updated_at == custom_updated_at
        
        finally:
            await client.drop_database(db.name)
            await client.close()
    
    @pytest.mark.asyncio
    async def test_timestamp_with_insert_many(self):
        
        # ARRANGE
        client, db = await init_via_uri(MONGO_URI, documents_list=document_list_1)
        
        try:
            
            for name in await db.list_collection_names():
                await db[name].delete_many({})
            
            # ARRANGE
            
            doc_with_default_timestamps_id = uuid.uuid4()
            doc_with_custom_created_at_timestamp_id = uuid.uuid4()
            doc_with_custom_updated_at_timestamp_id = uuid.uuid4()
            
            start_of_day = datetime.datetime.combine(datetime.datetime.now(tz=datetime.timezone.utc).date(), datetime.time.min)
            custom_created_at = start_of_day - datetime.timedelta(days=2)
            custom_updated_at = start_of_day - datetime.timedelta(days=1)
            
            doc_with_default_timestamps = SadLonelyDocument(
                id=doc_with_default_timestamps_id, operation_name=".insert_many()", description="doc_with_default_timestamps"
            )
            
            doc_with_custom_created_at_timestamps = SadLonelyDocument(
                id=doc_with_custom_created_at_timestamp_id,
                created_at=custom_created_at, operation_name=".insert_many()", description="doc_with_custom_created_at_timestamps"
            )
            
            doc_with_custom_update_at_timestamps = SadLonelyDocument(
                id=doc_with_custom_updated_at_timestamp_id,
                updated_at=custom_updated_at, operation_name=".insert_many()", description="doc_with_custom_update_at_timestamps"
            )
            
            # ACT & ASSERT
            
            
            inserted_many = await SadLonelyDocument.insert_many([doc_with_default_timestamps, doc_with_custom_created_at_timestamps, doc_with_custom_update_at_timestamps])
            
            assert inserted_many.acknowledged
            assert len(inserted_many.inserted_ids) == 3
            
            saved_doc_with_default_timestamps = await SadLonelyDocument.find_one(SadLonelyDocument.id == doc_with_default_timestamps_id)
            assert saved_doc_with_default_timestamps is not None
            assert saved_doc_with_default_timestamps.id == doc_with_default_timestamps_id
            assert saved_doc_with_default_timestamps.created_at == saved_doc_with_default_timestamps.updated_at
            assert saved_doc_with_default_timestamps.created_at.date() == datetime.datetime.now(datetime.timezone.utc).date()
            assert saved_doc_with_default_timestamps.updated_at.date() == datetime.datetime.now(datetime.timezone.utc).date()
            
            saved_doc_with_custom_created_at_timestamps = await SadLonelyDocument.find_one(SadLonelyDocument.id == doc_with_custom_created_at_timestamp_id)
            assert saved_doc_with_custom_created_at_timestamps is not None
            assert saved_doc_with_custom_created_at_timestamps.id == doc_with_custom_created_at_timestamp_id
            assert saved_doc_with_custom_created_at_timestamps.created_at == custom_created_at
            assert saved_doc_with_custom_created_at_timestamps.updated_at.date() == start_of_day.date()
            
            saved_doc_with_custom_updated_at_timestamps = await SadLonelyDocument.find_one(SadLonelyDocument.id == doc_with_custom_updated_at_timestamp_id)
            assert saved_doc_with_custom_updated_at_timestamps is not None
            assert saved_doc_with_custom_updated_at_timestamps.id == doc_with_custom_updated_at_timestamp_id
            assert saved_doc_with_custom_updated_at_timestamps.created_at.date() == start_of_day.date()
            assert saved_doc_with_custom_updated_at_timestamps.updated_at == custom_updated_at
        
        finally:
            await client.drop_database(db.name)
            await client.close()

class TestVanillaOnUpdate:
    
    @pytest.mark.asyncio
    async def test_timestamp_with_save(self):
        
        # ARRANGE
        client, db = await init_via_uri(MONGO_URI, documents_list=document_list_1)
        
        try:
            
            for name in await db.list_collection_names():
                await db[name].delete_many({})

            default_doc_id = uuid.uuid4()
            
            default_doc = SadLonelyDocument(
                id=default_doc_id, operation_name=".insert()", description="default_doc"
            )
            
            _ = await default_doc.insert()
            
            retrieved_default_doc = await SadLonelyDocument.find_one(SadLonelyDocument.id == default_doc_id)
            
            assert retrieved_default_doc is not None
            assert retrieved_default_doc.sad_field == 0
            
            retrieved_default_doc_with_default_timestamp = await SadLonelyDocument.find_one(SadLonelyDocument.id == default_doc_id)
            retrieved_default_doc_with_default_timestamp.sad_field = 100
            retrieved_default_doc_with_default_timestamp.operation_name = ".save()"
            retrieved_default_doc_with_default_timestamp.description = "the updated default_doc upserted via .save()"
            await retrieved_default_doc_with_default_timestamp.save()
            
            retrieved_default_doc_with_default_timestamp_after_update = await SadLonelyDocument.find_one(SadLonelyDocument.id == default_doc_id)
            
            assert retrieved_default_doc_with_default_timestamp_after_update
            assert retrieved_default_doc_with_default_timestamp_after_update.created_at == retrieved_default_doc.created_at
            assert retrieved_default_doc_with_default_timestamp_after_update.updated_at > retrieved_default_doc.updated_at
            
            start_of_day = datetime.datetime.combine(datetime.datetime.now(tz=datetime.timezone.utc).date(), datetime.time.min)
            custom_updated_at = start_of_day - datetime.timedelta(days=1)
            
            retrieved_default_with_custom_updated_at_doc = await SadLonelyDocument.find_one(SadLonelyDocument.id == default_doc_id)
            retrieved_default_with_custom_updated_at_doc.sad_field = 500
            retrieved_default_with_custom_updated_at_doc.updated_at = custom_updated_at
            retrieved_default_with_custom_updated_at_doc.operation_name = ".save()"
            retrieved_default_with_custom_updated_at_doc.description = "the updated default_doc with custom updated_at upserted via .save()"
            await retrieved_default_with_custom_updated_at_doc.save()
            
            retrieved_default_doc_with_custom_updated_at_timestamp_after_update = await SadLonelyDocument.find_one(SadLonelyDocument.id == default_doc_id)
            
            assert retrieved_default_doc_with_custom_updated_at_timestamp_after_update
            assert retrieved_default_doc_with_custom_updated_at_timestamp_after_update.created_at == retrieved_default_doc.created_at
            assert retrieved_default_doc_with_custom_updated_at_timestamp_after_update.updated_at == custom_updated_at
        
        finally:
            await client.drop_database(db.name)
            await client.close()
    
    @pytest.mark.asyncio
    async def test_timestamp_with_replace(self):
        
        # ARRANGE
        client, db = await init_via_uri(MONGO_URI, documents_list=document_list_1)
        
        try:
            
            for name in await db.list_collection_names():
                await db[name].delete_many({})
            
            default_doc_id = uuid.uuid4()
            
            default_doc = SadLonelyDocument(
                id=default_doc_id, operation_name=".insert()", description="default_doc"
            )
            
            _ = await default_doc.insert()
            
            retrieved_default_doc = await SadLonelyDocument.find_one(SadLonelyDocument.id == default_doc_id)
            
            assert retrieved_default_doc is not None
            assert retrieved_default_doc.sad_field == 0
            
            retrieved_default_doc_with_default_timestamp = await SadLonelyDocument.find_one(SadLonelyDocument.id == default_doc_id)
            retrieved_default_doc_with_default_timestamp.sad_field = 100
            retrieved_default_doc_with_default_timestamp.operation_name = ".replace()"
            retrieved_default_doc_with_default_timestamp.description = "the updated default_doc via .replace()"
            await retrieved_default_doc_with_default_timestamp.replace()
            
            retrieved_default_doc_with_default_timestamp_after_update = await SadLonelyDocument.find_one(SadLonelyDocument.id == default_doc_id)
            
            assert retrieved_default_doc_with_default_timestamp_after_update
            assert retrieved_default_doc_with_default_timestamp_after_update.created_at == retrieved_default_doc.created_at
            assert retrieved_default_doc_with_default_timestamp_after_update.updated_at > retrieved_default_doc.updated_at
            
            start_of_day = datetime.datetime.combine(datetime.datetime.now(tz=datetime.timezone.utc).date(), datetime.time.min)
            custom_updated_at = start_of_day - datetime.timedelta(days=1)
            
            retrieved_default_with_custom_updated_at_doc = await SadLonelyDocument.find_one(SadLonelyDocument.id == default_doc_id)
            retrieved_default_with_custom_updated_at_doc.sad_field = 500
            retrieved_default_with_custom_updated_at_doc.updated_at = custom_updated_at
            retrieved_default_with_custom_updated_at_doc.operation_name = ".replace()"
            retrieved_default_with_custom_updated_at_doc.description = "the updated default_doc with custom updated_at upserted via .replace()"
            await retrieved_default_with_custom_updated_at_doc.save()
            
            retrieved_default_doc_with_custom_updated_at_timestamp_after_update = await SadLonelyDocument.find_one(SadLonelyDocument.id == default_doc_id)
            
            assert retrieved_default_doc_with_custom_updated_at_timestamp_after_update
            assert retrieved_default_doc_with_custom_updated_at_timestamp_after_update.created_at == retrieved_default_doc.created_at
            assert retrieved_default_doc_with_custom_updated_at_timestamp_after_update.updated_at == custom_updated_at
        
        finally:
            await client.drop_database(db.name)
            await client.close()
    
    @pytest.mark.asyncio
    async def test_timestamp_with_update(self):
        
        # ARRANGE
        client, db = await init_via_uri(MONGO_URI, documents_list=document_list_1)
        
        try:
            
            for name in await db.list_collection_names():
                await db[name].delete_many({})
            
            start_of_day = datetime.datetime.combine(datetime.datetime.now(tz=datetime.timezone.utc).date(), datetime.time.min)
            custom_updated_at = start_of_day - datetime.timedelta(days=1)
            
            default_doc_id = uuid.uuid4()
            
            default_doc = SadLonelyDocument(
                id=default_doc_id, operation_name=".insert()", description="default_doc"
            )
            
            _ = await default_doc.insert()
            
            retrieved_default_doc = await SadLonelyDocument.find_one(SadLonelyDocument.id == default_doc_id)
            
            assert retrieved_default_doc is not None
            assert retrieved_default_doc.sad_field == 0
            
            retrieved_default_doc_with_default_timestamp = await SadLonelyDocument.find_one(SadLonelyDocument.id == default_doc_id)
            await retrieved_default_doc_with_default_timestamp.update(
                Set({
                    SadLonelyDocument.sad_field: 100,
                    SadLonelyDocument.operation_name: ".replace()",
                    SadLonelyDocument.description: "the updated default_doc via .replace()",
                })
            )
            
            retrieved_default_doc_with_default_timestamp_after_update = await SadLonelyDocument.find_one(SadLonelyDocument.id == default_doc_id)
            
            assert retrieved_default_doc_with_default_timestamp_after_update
            assert retrieved_default_doc_with_default_timestamp_after_update.created_at == retrieved_default_doc.created_at
            # They remain equal because .update does not kick the After Event, its a none instance based raw query closer to the DB
            assert retrieved_default_doc_with_default_timestamp_after_update.updated_at == retrieved_default_doc.updated_at
            
            retrieved_default_with_custom_updated_at_doc = await SadLonelyDocument.find_one(SadLonelyDocument.id == default_doc_id)
            await retrieved_default_with_custom_updated_at_doc.update(
                Set({
                    SadLonelyDocument.sad_field: 500,
                    SadLonelyDocument.operation_name: ".update()",
                    SadLonelyDocument.updated_at: custom_updated_at,
                    SadLonelyDocument.description: "the updated default_doc with custom updated_at via .update()",
                })
            )
            
            retrieved_default_doc_with_custom_updated_at_timestamp_after_update = await SadLonelyDocument.find_one(SadLonelyDocument.id == default_doc_id)
            
            assert retrieved_default_doc_with_custom_updated_at_timestamp_after_update
            assert retrieved_default_doc_with_custom_updated_at_timestamp_after_update.created_at == retrieved_default_doc.created_at
            assert retrieved_default_doc_with_custom_updated_at_timestamp_after_update.updated_at == custom_updated_at
        
        finally:
            await client.drop_database(db.name)
            await client.close()
    
