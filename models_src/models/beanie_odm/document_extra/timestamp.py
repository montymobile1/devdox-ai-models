from datetime import datetime, timezone

from beanie import before_event
from beanie.odm.actions import EventTypes
from pydantic import BaseModel, Field, PrivateAttr

"""
EventTypes are handled in /beanie/odm/documents.py
"""

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)

class TimestampAuditMixin(BaseModel):
    
    created_at: datetime = Field(
        default_factory=_now_utc,
        description="Record creation timestamp",
    )
    updated_at: datetime = Field(
        default_factory=_now_utc,
        description="Record last update timestamp",
    )
    
    # private guard: was updated_at explicitly set on this instance since last save?
    _explicit_updated_at: bool = PrivateAttr(default=False)
    
    def __setattr__(self, name, value):
        # mark when user explicitly sets updated_at
        if name == "updated_at":
            object.__setattr__(self, "_explicit_updated_at", True)
        super().__setattr__(name, value)
    
    # On first insert: set both
    @before_event(EventTypes.INSERT)
    def _set_created(self):
        now = _now_utc()
        
        fields_set = getattr(self, "model_fields_set", set())
        created_explicit = "created_at" in fields_set
        updated_explicit = "updated_at" in fields_set
        
        # created_at: use explicit if provided, else now
        self.created_at = self.created_at if created_explicit else now
        
        # updated_at: use explicit if provided, else now
        self.updated_at = self.updated_at if updated_explicit else now
    
    
    @before_event([EventTypes.SAVE, EventTypes.REPLACE, EventTypes.SAVE_CHANGES])
    def _touch_instance_based_update(self):
        """
        Touch updated_at only for instance-style saves, and only if user didn't explicitly set updated_at.
        `EventTypes.UPDATE` is ignored here cause it executes a Raw Query so everything needs to be set manually
        """
        if not self._explicit_updated_at:
            self.updated_at = _now_utc()
        # clear the guard so next change can auto-touch again
        self._explicit_updated_at = False
