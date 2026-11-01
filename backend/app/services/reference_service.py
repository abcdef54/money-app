"""CRUD for reference entities: accounts, categories, merchants, locations, tags."""
from fastapi import HTTPException
from sqlalchemy import func, select, update as sa_update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Account, Category, Expense, Location, Merchant, Tag
from app.schemas.reference import (
    AccountCreate,
    AccountUpdate,
    CategoryCreate,
    CategoryTree,
    CategoryUpdate,
    LocationCreate,
    MerchantCreate,
    MerchantMerge,
    MerchantUpdate,
    TagCreate,
)


def _get_or_404(db: Session, model, obj_id: int):
    obj = db.get(model, obj_id)
    if obj is None:
        raise HTTPException(status_code=404, detail=f"{model.__name__} not found")
    return obj


# --- Accounts ----------------------------------------------------------
def list_accounts(db: Session, include_inactive: bool = False) -> list[Account]:
    query = select(Account).order_by(Account.name)
    if not include_inactive:
        query = query.where(Account.active.is_(True))
    return list(db.scalars(query))


def create_account(db: Session, data: AccountCreate) -> Account:
    account = Account(**data.model_dump())
    db.add(account)
    db.commit()
    return account


def update_account(db: Session, account_id: int, data: AccountUpdate) -> Account:
    account = _get_or_404(db, Account, account_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(account, key, value)
    db.commit()
    return account


def delete_account(db: Session, account_id: int) -> None:
    """Deactivate rather than delete when transactions reference the account."""
    account = _get_or_404(db, Account, account_id)
    in_use = db.scalar(select(Expense.id).where(Expense.account_id == account_id).limit(1))
    if in_use:
        account.active = False
    else:
        db.delete(account)
    db.commit()


# --- Categories --------------------------------------------------------
def list_categories(db: Session, include_inactive: bool = False) -> list[Category]:
    query = select(Category).order_by(Category.sort_order, Category.name)
    if not include_inactive:
        query = query.where(Category.active.is_(True))
    return list(db.scalars(query))


def category_tree(db: Session, include_inactive: bool = False) -> list[CategoryTree]:
    categories = list_categories(db, include_inactive)
    nodes = {c.id: CategoryTree.model_validate(c) for c in categories}
    roots: list[CategoryTree] = []
    for node in nodes.values():
        if node.parent_id and node.parent_id in nodes:
            nodes[node.parent_id].children.append(node)
        else:
            roots.append(node)
    return roots


def _check_duplicate_category(
    db: Session, name: str, parent_id: int | None, exclude_id: int | None = None
) -> None:
    """Reject duplicate sibling names (case-insensitive). Together with the
    unique DB index this makes duplicate creation impossible even under
    concurrent requests (e.g. rapid double-clicks)."""
    query = select(Category.id).where(
        func.lower(Category.name) == name.strip().lower(),
        Category.parent_id.is_(None) if parent_id is None else Category.parent_id == parent_id,
    )
    if exclude_id is not None:
        query = query.where(Category.id != exclude_id)
    if db.scalar(query.limit(1)):
        raise HTTPException(status_code=400, detail=f'Category "{name}" already exists here')


def create_category(db: Session, data: CategoryCreate) -> Category:
    if data.parent_id is not None:
        _get_or_404(db, Category, data.parent_id)
    _check_duplicate_category(db, data.name, data.parent_id)
    category = Category(**data.model_dump())
    db.add(category)
    try:
        db.commit()
    except IntegrityError:
        # Unique index caught a race the pre-check missed.
        db.rollback()
        raise HTTPException(status_code=400, detail=f'Category "{data.name}" already exists here')
    return category


def update_category(db: Session, category_id: int, data: CategoryUpdate) -> Category:
    category = _get_or_404(db, Category, category_id)
    fields = data.model_dump(exclude_unset=True)
    if "name" in fields or "parent_id" in fields:
        _check_duplicate_category(
            db,
            fields.get("name", category.name),
            fields.get("parent_id", category.parent_id),
            exclude_id=category_id,
        )
    new_parent = fields.get("parent_id")
    if new_parent is not None:
        if new_parent == category_id:
            raise HTTPException(status_code=400, detail="A category cannot be its own parent")
        # Walk up from the new parent to detect cycles.
        cursor = db.get(Category, new_parent)
        while cursor is not None:
            if cursor.id == category_id:
                raise HTTPException(status_code=400, detail="Move would create a category cycle")
            cursor = cursor.parent
    for key, value in fields.items():
        setattr(category, key, value)
    db.commit()
    return category


def delete_category(db: Session, category_id: int) -> None:
    """Deactivate when in use (expenses keep their history), delete otherwise."""
    category = _get_or_404(db, Category, category_id)
    in_use = db.scalar(select(Expense.id).where(Expense.category_id == category_id).limit(1))
    has_children = db.scalar(select(Category.id).where(Category.parent_id == category_id).limit(1))
    if in_use or has_children:
        category.active = False
    else:
        db.delete(category)
    db.commit()


# --- Merchants ---------------------------------------------------------
def list_merchants(db: Session, search: str | None = None, include_inactive: bool = False) -> list[Merchant]:
    query = select(Merchant).order_by(Merchant.name)
    if not include_inactive:
        query = query.where(Merchant.active.is_(True))
    if search:
        query = query.where(Merchant.name.ilike(f"%{search}%"))
    return list(db.scalars(query))


def create_merchant(db: Session, data: MerchantCreate) -> Merchant:
    merchant = Merchant(**data.model_dump())
    db.add(merchant)
    db.commit()
    return merchant


def update_merchant(db: Session, merchant_id: int, data: MerchantUpdate) -> Merchant:
    merchant = _get_or_404(db, Merchant, merchant_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(merchant, key, value)
    db.commit()
    return merchant


def delete_merchant(db: Session, merchant_id: int) -> None:
    merchant = _get_or_404(db, Merchant, merchant_id)
    in_use = db.scalar(select(Expense.id).where(Expense.merchant_id == merchant_id).limit(1))
    if in_use:
        merchant.active = False
    else:
        db.delete(merchant)
    db.commit()


def merge_merchants(db: Session, data: MerchantMerge) -> Merchant:
    """Reassign all expenses from source merchants to the target, then
    remove the duplicates."""
    target = _get_or_404(db, Merchant, data.target_id)
    if data.target_id in data.source_ids:
        raise HTTPException(status_code=400, detail="Target cannot be one of the sources")
    for source_id in data.source_ids:
        _get_or_404(db, Merchant, source_id)
    db.execute(
        sa_update(Expense)
        .where(Expense.merchant_id.in_(data.source_ids))
        .values(merchant_id=data.target_id)
    )
    for source_id in data.source_ids:
        db.delete(db.get(Merchant, source_id))
    db.commit()
    return target


# --- Locations ---------------------------------------------------------
def list_locations(db: Session) -> list[Location]:
    return list(db.scalars(select(Location).order_by(Location.name)))


def create_location(db: Session, data: LocationCreate) -> Location:
    location = Location(**data.model_dump())
    db.add(location)
    db.commit()
    return location


def delete_location(db: Session, location_id: int) -> None:
    db.delete(_get_or_404(db, Location, location_id))
    db.commit()


# --- Tags --------------------------------------------------------------
def list_tags(db: Session) -> list[Tag]:
    return list(db.scalars(select(Tag).order_by(Tag.name)))


def create_tag(db: Session, data: TagCreate) -> Tag:
    existing = db.scalar(select(Tag).where(Tag.name == data.name))
    if existing:
        raise HTTPException(status_code=400, detail="Tag already exists")
    tag = Tag(**data.model_dump())
    db.add(tag)
    db.commit()
    return tag


def delete_tag(db: Session, tag_id: int) -> None:
    db.delete(_get_or_404(db, Tag, tag_id))
    db.commit()
