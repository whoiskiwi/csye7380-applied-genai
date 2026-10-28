"""Build SDK agents on the configured backend and run them with retry and statistics."""
from __future__ import annotations

import json
import os
from pathlib import Path

from agents import Agent, ModelSettings, OpenAIChatCompletionsModel, Runner, set_tracing_disabled
from openai import AsyncOpenAI

from ers.agents.llm_cache import CachingModel
from ers.agents.mock_model import MockModel
from ers.config import load_yaml

PROMPT_DIR = Path(__file__).parent / "prompts"
set_tracing_disabled(True)          # no trace upload; we keep our own event log


def prompt(name: str, **fmt) -> str:
    text = (PROMPT_DIR / f"{name}.md").read_text(encoding="utf-8")
    for k, v in fmt.items():
        text = text.replace("{" + k + "}", str(v))
    return text


def prompt_version(name: str) -> str:
    first = (PROMPT_DIR / f"{name}.md").read_text(encoding="utf-8").splitlines()[0]
    return first.replace("<!--", "").replace("-->", "").replace("prompt version:", "").strip()


class AgentRuntime:
    def __init__(self, backend: str | None = None, cache_mode: str | None = None):
        cfg = load_yaml("models.yaml")
        self.cfg = cfg
        self.backend = backend or cfg["backend"]
        self.cache_mode = cache_mode or cfg.get("cache_mode", "record")
        self._models: dict[str, object] = {}
        self.calls = self.failures = self.retries = 0
        self.soft_retries = self.soft_violations = 0     # role-rule checks (see `soft`)
        self.rule_log: list[dict] = []                    # each role-rule violation and whether the retry fixed it
        self.tokens_in = self.tokens_out = 0
        self.per_agent: dict[str, int] = {}
        self.errors: list[str] = []

    def model_name(self, agent_key: str) -> str:
        if self.backend == "mock":
            return "mock"
        tier = self.cfg["agents"].get(agent_key, "fast")
        override = os.environ.get(f"ERS_MODEL_{tier.upper()}")      # e.g. ERS_MODEL_STRONG=qwen2.5:14b on the cluster
        if override:
            return override
        return self.cfg["tiers"][tier][self.backend] if tier in self.cfg["tiers"] else tier

    def model(self, agent_key: str):
        name = self.model_name(agent_key)
        if name not in self._models:
            if self.backend == "mock":
                inner = MockModel()
            elif self.backend == "ollama":
                base_url = os.environ.get("ERS_OLLAMA_BASE_URL", self.cfg["ollama_base_url"])
                client = AsyncOpenAI(base_url=base_url, api_key="ollama", timeout=300)
                inner = OpenAIChatCompletionsModel(model=name, openai_client=client)
            else:
                inner = OpenAIChatCompletionsModel(model=name, openai_client=AsyncOpenAI())
            self._models[name] = inner if self.backend == "mock" else CachingModel(inner, f"{self.backend}:{name}",
                                                                                 self.cache_mode)
        return self._models[name]

    def info(self) -> dict:
        return {"backend": self.backend, "cache_mode": self.cache_mode,
                "models": {k: self.model_name(k) for k in self.cfg["agents"]},
                "prompts": {p.stem: prompt_version(p.stem) for p in sorted(PROMPT_DIR.glob("*.md"))
                            if not p.name.startswith(".")}}

    def run(self, agent_key: str, display_name: str, instructions: str, output_type, task: dict, tools=None,
            validate=None, soft=None):
        """Return the parsed output object, or None after one failed retry (caller falls back to rules).

        `validate` checks hard errors (missing decisions): failing twice means fallback.
        `soft` checks the agent's own role rules: the first violation is sent back once with the reason;
        the second answer is used whatever it is (the agent keeps the decision), and the violation is counted."""
        agent = Agent(name=display_name, instructions=instructions, model=self.model(agent_key),
                      model_settings=ModelSettings(temperature=self.cfg.get("temperature", 0)),
                      output_type=output_type, tools=tools or [])
        text = json.dumps(task, ensure_ascii=False, separators=(",", ":"))
        last_err = rule_msg = None
        for attempt in range(2):
            self.calls += 1
            self.per_agent[agent_key] = self.per_agent.get(agent_key, 0) + 1
            try:
                if attempt == 0:
                    inp = text
                elif rule_msg:
                    inp = text + f"\n\nYour previous answer broke a rule of your role ({rule_msg}). Answer again."
                else:
                    inp = text + (f"\n\nYour previous answer was invalid ({last_err}). "
                                  "Return valid JSON that follows the schema exactly.")
                res = Runner.run_sync(agent, inp, max_turns=4)
                for r in res.raw_responses:
                    self.tokens_in += r.usage.input_tokens
                    self.tokens_out += r.usage.output_tokens
                problem = validate(res.final_output) if validate else None
                if problem:
                    raise ValueError(problem)
                rule = soft(res.final_output) if soft else None
                if rule and attempt == 0:
                    self.soft_retries += 1
                    rule_msg = rule
                    continue
                if rule:
                    self.soft_violations += 1
                if rule_msg:
                    self.rule_log.append({"agent": agent_key, "rule": rule_msg, "fixed_by_retry": not rule})
                return res.final_output
            except Exception as e:      # invalid JSON, schema error, max turns, network...
                rule_msg = None
                last_err = f"{type(e).__name__}: {str(e)[:200]}"
                self.errors.append(f"{agent_key}: {last_err}")
                if attempt == 0:
                    self.retries += 1
        self.failures += 1
        return None
