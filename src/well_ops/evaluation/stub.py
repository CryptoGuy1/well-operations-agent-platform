"""A stub model for dry runs of the harness: no provider calls, synthetic token counts.

The stub writes its review from the answer key, so a dry run exercises every scoring path. An
agent stub first calls `well_overview` (when it has the tool), then submits a first draft that
states every other key fact with the evidence the checker accepts, one contradicted value and one
unclaimed number; on the checker's findings it submits a final draft with the value corrected and
the unclaimed sentence dropped. A baseline stub submits every third fact without evidence, one
value wrong.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from anthropic.types import Message

from well_ops.agents.checker import METRICS, Checker
from well_ops.agents.runtime import SUBMIT
from well_ops.agents.schema import UNITS
from well_ops.evaluation.answer_key import SECTION_COUNT, Fact, WellboreKey

USAGE = {"input_tokens": 2000, "output_tokens": 1000, "cache_read_input_tokens": 0}


def _message(n: int, block: dict[str, Any]) -> Message:
    return Message.model_validate(
        {
            "id": f"msg_stub_{n}",
            "type": "message",
            "role": "assistant",
            "model": "stub",
            "content": [block],
            "stop_reason": "tool_use",
            "stop_sequence": None,
            "usage": USAGE,
        }
    )


def _use(n: int, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    return {"type": "tool_use", "id": f"toolu_stub_{n}", "name": name, "input": arguments}


class StubModel:
    def __init__(
        self, key: WellboreKey, checker: Checker, *, agent: str, with_evidence: bool
    ) -> None:
        self._key = key
        self._checker = checker
        self._agent = agent
        self._with_evidence = with_evidence

    async def count_tokens(self, params: Mapping[str, Any]) -> int:
        return 1000 + len(json.dumps(params["messages"], default=str)) // 4

    async def create(self, params: Mapping[str, Any]) -> Message:
        messages = params["messages"]
        turn = sum(m["role"] == "assistant" for m in messages)
        tools = {t["name"] for t in params["tools"]}
        if turn == 0 and "well_overview" in tools:
            return _message(
                turn, _use(turn, "well_overview", {"wellbore_key": self._key.wellbore_name})
            )
        revising = self._with_evidence and "claim checker found" in json.dumps(
            messages[-1]["content"], default=str
        )
        return _message(turn, _use(turn, SUBMIT, self._document(final=revising)))

    def _claim(self, n: int, fact: Fact, value: Any) -> dict[str, Any]:
        claim_type = next(iter(METRICS[fact.metric].types))
        evidence = (
            sorted(self._checker.compute(fact.metric, fact.scope).supporting)
            if self._with_evidence
            else []
        )
        return {
            "id": f"c{n}",
            "type": str(claim_type),
            "value": value,
            "unit": UNITS[claim_type],
            "evidence_ids": evidence,
            "what": {"metric": fact.metric, **fact.scope},
        }

    def _document(self, *, final: bool) -> dict[str, Any]:
        facts = [f for f in self._key.facts if f.metric != SECTION_COUNT]
        chosen = facts[::2] if self._with_evidence else facts[::3]
        sentences = []
        wrong = next(
            (i for i, f in enumerate(chosen) if isinstance(f.value, float) and f.value > 0), None
        )
        for i, fact in enumerate(chosen):
            value: Any = fact.value
            if i == wrong and not final:
                value = round(float(value) * 1.5, 2)
            unit = UNITS[next(iter(METRICS[fact.metric].types))]
            where = ", ".join(f"{k} {v}" for k, v in fact.scope.items() if k != "wellbore")
            text = f"The {fact.metric.replace('_', ' ')} ({where or 'wellbore'}) is {value}"
            sentences.append(
                {
                    "text": text + (f" {unit}." if unit else "."),
                    "claims": [self._claim(i, fact, value)],
                }
            )
        if self._with_evidence and not final:
            sentences.append({"text": "The rig worked with 7 crews.", "claims": []})
        return {
            "agent": self._agent,
            "title": f"End-of-well review: {self._key.wellbore_name}",
            "sections": [{"heading": "Stub review", "sentences": sentences}],
        }
