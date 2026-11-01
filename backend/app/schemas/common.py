"""Shared schema helpers."""
from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    """Base for schemas hydrated from SQLAlchemy objects."""

    model_config = ConfigDict(from_attributes=True)
