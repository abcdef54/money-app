"""Assemble the API router. New modules (e.g. a future /ml router) plug in here."""
from fastapi import APIRouter

from app.api.routes import analytics, expenses, incomes, planning, reference

api_router = APIRouter(prefix="/api")
api_router.include_router(expenses.router)
api_router.include_router(incomes.router)
api_router.include_router(reference.router)
api_router.include_router(planning.router)
api_router.include_router(analytics.router)
