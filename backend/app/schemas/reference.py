"""Schemas for Account, Category, Merchant, Location, Tag."""
from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


# --- Account -----------------------------------------------------------
class AccountBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    account_type: str = "cash"
    currency: str = "VND"
    bank: str | None = None
    active: bool = True


class AccountCreate(AccountBase):
    pass


class AccountUpdate(BaseModel):
    name: str | None = None
    account_type: str | None = None
    currency: str | None = None
    bank: str | None = None
    active: bool | None = None


class AccountOut(ORMModel, AccountBase):
    id: int


# --- Category ----------------------------------------------------------
class CategoryBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    parent_id: int | None = None
    icon: str | None = None
    color: str | None = None
    active: bool = True
    budgetable: bool = True
    sort_order: int = 0


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: str | None = None
    parent_id: int | None = None
    icon: str | None = None
    color: str | None = None
    active: bool | None = None
    budgetable: bool | None = None
    sort_order: int | None = None


class CategoryOut(ORMModel, CategoryBase):
    id: int


class CategoryTree(CategoryOut):
    children: list["CategoryTree"] = []


# --- Merchant ----------------------------------------------------------
class MerchantBase(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    category_hint_id: int | None = None
    notes: str | None = None
    active: bool = True


class MerchantCreate(MerchantBase):
    pass


class MerchantUpdate(BaseModel):
    name: str | None = None
    category_hint_id: int | None = None
    notes: str | None = None
    active: bool | None = None


class MerchantOut(ORMModel, MerchantBase):
    id: int


class MerchantMerge(BaseModel):
    source_ids: list[int] = Field(min_length=1)
    target_id: int


# --- Location ----------------------------------------------------------
class LocationBase(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class LocationCreate(LocationBase):
    pass


class LocationOut(ORMModel, LocationBase):
    id: int


# --- Tag ---------------------------------------------------------------
class TagBase(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    color: str | None = None


class TagCreate(TagBase):
    pass


class TagOut(ORMModel, TagBase):
    id: int
