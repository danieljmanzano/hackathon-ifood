"""Orçamento do agente nutricional propagado às chamadas HTTP via ContextVar."""

from contextvars import ContextVar
from dataclasses import dataclass

from app.core.exceptions import AppError
from app.storage.catalog import CatalogStore


class NutritionBudgetExceeded(AppError):
    def __init__(self, reason):
        self.reason = reason
        super().__init__(
            "Enriquecimento nutricional pausado pelo limite de uso.", status_code=429, code=reason
        )


@dataclass
class Budget:
    store: CatalogStore
    settings: object
    product: str
    reason: str | None = None

    def reserve(self, provider):
        self.reason = self.store.reserve(
            self.product,
            self.settings.catalog_calls_per_day,
            self.settings.catalog_products_per_day,
            self.settings.catalog_calls_per_product,
        )
        if self.reason:
            raise NutritionBudgetExceeded(self.reason)
        from app.core import logs

        logs.info("orçamento nutrição", f"chamada reservada: {provider}")


current_budget: ContextVar[Budget | None] = ContextVar("nutrition_budget", default=None)


def reserve_call(provider):
    budget = current_budget.get()
    if budget:
        budget.reserve(provider)


def output_limit(default=None):
    budget = current_budget.get()
    return (
        min(default, budget.settings.catalog_max_output_tokens)
        if budget and default
        else (budget.settings.catalog_max_output_tokens if budget else default)
    )


def check_input(value):
    budget = current_budget.get()
    if budget and len(str(value)) > budget.settings.catalog_max_input_chars:
        raise NutritionBudgetExceeded("input_limit")
