"""The release budget (evaluation/RULES.md): a hard cap in USD for every model call of a release.

Before each call the guard counts the request's prompt tokens and bounds the call's cost: the
counted prompt plus a 10 % margin at the highest input-side price of either tier, plus the full
response cap at the highest output price of either tier. If the spend so far plus that bound
would exceed the cap, the call is not made and `BudgetExceeded` is raised. After the call, its
cost from the logged usage is added to the spend.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from anthropic.types import Message

from well_ops.agents.audit_log import Prices
from well_ops.agents.runtime import ModelClient, TokenCounter

PROMPT_MARGIN = 1.1


class BudgetExceeded(Exception):
    """The next model call could take the release over its budget."""


@dataclass
class Budget:
    cap_usd: float
    spent_usd: float = 0.0

    def reserve(self, bound_usd: float) -> None:
        if self.spent_usd + bound_usd > self.cap_usd:
            raise BudgetExceeded(
                f"spent USD {self.spent_usd:.4f}; the next call could cost up to "
                f"USD {bound_usd:.4f}; cap USD {self.cap_usd}"
            )

    def add(self, cost_usd: float) -> None:
        self.spent_usd += cost_usd


def call_bound(prices: Prices, prompt_tokens: int, max_tokens: int) -> float:
    """The most one call can cost: the prompt (with margin) at the highest input-side price and
    the whole response cap at the highest output price, over both tiers."""
    inputs = [
        p
        for p in (
            prices.input_per_mtok_usd,
            prices.cache_write_per_mtok_usd,
            prices.cache_read_per_mtok_usd,
            prices.above_input_per_mtok_usd,
            prices.above_cache_write_per_mtok_usd,
            prices.above_cache_read_per_mtok_usd,
        )
        if p is not None
    ]
    outputs = [
        p for p in (prices.output_per_mtok_usd, prices.above_output_per_mtok_usd) if p is not None
    ]
    prompt = math.ceil(prompt_tokens * PROMPT_MARGIN)
    return (prompt * max(inputs) + max_tokens * max(outputs)) / 1e6


def _usage(message: Message) -> dict[str, int]:
    u = message.usage
    return {
        "input_tokens": u.input_tokens,
        "output_tokens": u.output_tokens,
        "cache_creation_input_tokens": u.cache_creation_input_tokens or 0,
        "cache_read_input_tokens": u.cache_read_input_tokens or 0,
    }


class BudgetedModel:
    """A model client that checks the budget before every call and records its cost after."""

    def __init__(
        self,
        model: ModelClient,
        counter: TokenCounter,
        budget: Budget,
        prices: Prices,
        max_tokens: int,
    ) -> None:
        self._model = model
        self._counter = counter
        self._budget = budget
        self._prices = prices
        self._max_tokens = max_tokens

    async def create(self, params: Mapping[str, Any]) -> Message:
        prompt = await self._counter.count_tokens(params)
        bound = call_bound(self._prices, prompt, self._max_tokens)
        self._budget.reserve(bound)
        message = await self._model.create(params)
        cost = self._prices.cost(_usage(message))
        self._budget.add(bound if cost is None else cost)  # unknown cost counts at its bound
        return message
