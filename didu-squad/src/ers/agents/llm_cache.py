"""Record / replay cache around any SDK Model, keyed by everything that determines the reply."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from openai.types.responses import ResponseOutputItem
from pydantic import TypeAdapter

from agents.items import ModelResponse
from agents.models.interface import Model
from agents.usage import Usage

from ers.config import ROOT

CACHE_DIR = ROOT / "data" / "cache" / "llm"
_ITEMS = TypeAdapter(list[ResponseOutputItem])


class CacheMiss(RuntimeError):
    pass


class CachingModel(Model):
    def __init__(self, inner: Model, model_name: str, mode: str = "record"):
        self.inner, self.model_name, self.mode = inner, model_name, mode
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self.hits = self.misses = 0

    def _key(self, system_instructions, input, tools, output_schema) -> str:
        blob = json.dumps({
            "model": self.model_name,
            "system": system_instructions,
            "input": input if isinstance(input, str) else [dict(i) if isinstance(i, dict) else str(i) for i in input],
            "tools": sorted(getattr(t, "name", str(t)) for t in tools),
            "schema": output_schema.name() if output_schema else None,
        }, sort_keys=True, default=str)
        return hashlib.sha256(blob.encode()).hexdigest()

    async def get_response(self, system_instructions, input, model_settings, tools, output_schema, handoffs,
                           tracing, **kwargs) -> ModelResponse:
        key = self._key(system_instructions, input, tools, output_schema)
        path: Path = CACHE_DIR / f"{key}.json"
        if self.mode != "live" and path.exists():
            self.hits += 1
            data = json.loads(path.read_text())
            return ModelResponse(output=_ITEMS.validate_python(data["output"]),
                                 usage=Usage(**data.get("usage", {})), response_id=None)
        if self.mode == "replay":
            raise CacheMiss(key)
        self.misses += 1
        resp = await self.inner.get_response(system_instructions, input, model_settings, tools, output_schema,
                                             handoffs, tracing, **kwargs)
        if self.mode == "record":
            u = resp.usage
            path.write_text(json.dumps({
                "model": self.model_name,
                "output": [o.model_dump(mode="json") for o in resp.output],
                "usage": {"requests": u.requests, "input_tokens": u.input_tokens, "output_tokens": u.output_tokens,
                          "total_tokens": u.total_tokens},
            }))
        return resp

    def stream_response(self, *args, **kwargs):
        raise NotImplementedError
