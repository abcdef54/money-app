"""Endpoints for accounts, categories, merchants, locations, tags."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.reference import (
    AccountCreate,
    AccountOut,
    AccountUpdate,
    CategoryCreate,
    CategoryOut,
    CategoryTree,
    CategoryUpdate,
    LocationCreate,
    LocationOut,
    MerchantCreate,
    MerchantMerge,
    MerchantOut,
    MerchantUpdate,
    TagCreate,
    TagOut,
)
from app.services import reference_service as svc

router = APIRouter(tags=["reference"])


# --- Accounts ----------------------------------------------------------
@router.get("/accounts", response_model=list[AccountOut])
def list_accounts(include_inactive: bool = False, db: Session = Depends(get_db)):
    return svc.list_accounts(db, include_inactive)


@router.post("/accounts", response_model=AccountOut, status_code=201)
def create_account(data: AccountCreate, db: Session = Depends(get_db)):
    return svc.create_account(db, data)


@router.patch("/accounts/{account_id}", response_model=AccountOut)
def update_account(account_id: int, data: AccountUpdate, db: Session = Depends(get_db)):
    return svc.update_account(db, account_id, data)


@router.delete("/accounts/{account_id}", status_code=204)
def delete_account(account_id: int, db: Session = Depends(get_db)) -> None:
    svc.delete_account(db, account_id)


# --- Categories --------------------------------------------------------
@router.get("/categories", response_model=list[CategoryOut])
def list_categories(include_inactive: bool = False, db: Session = Depends(get_db)):
    return svc.list_categories(db, include_inactive)


@router.get("/categories/tree", response_model=list[CategoryTree])
def get_category_tree(include_inactive: bool = False, db: Session = Depends(get_db)):
    return svc.category_tree(db, include_inactive)


@router.post("/categories", response_model=CategoryOut, status_code=201)
def create_category(data: CategoryCreate, db: Session = Depends(get_db)):
    return svc.create_category(db, data)


@router.patch("/categories/{category_id}", response_model=CategoryOut)
def update_category(category_id: int, data: CategoryUpdate, db: Session = Depends(get_db)):
    return svc.update_category(db, category_id, data)


@router.delete("/categories/{category_id}", status_code=204)
def delete_category(category_id: int, db: Session = Depends(get_db)) -> None:
    svc.delete_category(db, category_id)


# --- Merchants ---------------------------------------------------------
@router.get("/merchants", response_model=list[MerchantOut])
def list_merchants(
    search: str | None = None, include_inactive: bool = False, db: Session = Depends(get_db)
):
    return svc.list_merchants(db, search, include_inactive)


@router.post("/merchants", response_model=MerchantOut, status_code=201)
def create_merchant(data: MerchantCreate, db: Session = Depends(get_db)):
    return svc.create_merchant(db, data)


@router.patch("/merchants/{merchant_id}", response_model=MerchantOut)
def update_merchant(merchant_id: int, data: MerchantUpdate, db: Session = Depends(get_db)):
    return svc.update_merchant(db, merchant_id, data)


@router.delete("/merchants/{merchant_id}", status_code=204)
def delete_merchant(merchant_id: int, db: Session = Depends(get_db)) -> None:
    svc.delete_merchant(db, merchant_id)


@router.post("/merchants/merge", response_model=MerchantOut)
def merge_merchants(data: MerchantMerge, db: Session = Depends(get_db)):
    return svc.merge_merchants(db, data)


# --- Locations ---------------------------------------------------------
@router.get("/locations", response_model=list[LocationOut])
def list_locations(db: Session = Depends(get_db)):
    return svc.list_locations(db)


@router.post("/locations", response_model=LocationOut, status_code=201)
def create_location(data: LocationCreate, db: Session = Depends(get_db)):
    return svc.create_location(db, data)


@router.delete("/locations/{location_id}", status_code=204)
def delete_location(location_id: int, db: Session = Depends(get_db)) -> None:
    svc.delete_location(db, location_id)


# --- Tags --------------------------------------------------------------
@router.get("/tags", response_model=list[TagOut])
def list_tags(db: Session = Depends(get_db)):
    return svc.list_tags(db)


@router.post("/tags", response_model=TagOut, status_code=201)
def create_tag(data: TagCreate, db: Session = Depends(get_db)):
    return svc.create_tag(db, data)


@router.delete("/tags/{tag_id}", status_code=204)
def delete_tag(tag_id: int, db: Session = Depends(get_db)) -> None:
    svc.delete_tag(db, tag_id)
