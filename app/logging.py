from __future__ import annotations

import datetime
import json
import logging
import os
import sys
import time
import uuid
from typing import Any, Dict, Optional

from langchain_core.callbacks import BaseCallbackHandler


def get_logger(name="audit"):
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        h = logging.StreamHandler()
        fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", "%Y-%m-%d %H:%M:%S")
        h.setFormatter(fmt)
        logger.addHandler(h)
    return logger


def _safe_get_id(serialized) -> str:
    # serialized might be None or a dict-like
    try:
        if isinstance(serialized, dict):
            # LangChain often uses {'id': ['langchain','chains',...]} shape
            v = serialized.get("id")
            if isinstance(v, (list, tuple)):
                return ".".join(str(x) for x in v)
            return str(v)
    except Exception:
        pass
    return "<unknown>"


def _safe_first_text(response):
    try:
        # Newer LC responses
        gens = getattr(response, "generations", None)
        if gens and len(gens) > 0 and len(gens[0]) > 0:
            return gens[0][0].text
    except Exception:
        pass
    # Fallbacks
    return getattr(response, "content", None) or "<unparseable>"


def _ts() -> str:
    return datetime.datetime.utcnow().isoformat(timespec="milliseconds") + "Z"


def _default(o: Any):
    # Make anything JSON-able
    if isinstance(o, (datetime.datetime, datetime.date)):
        return o.isoformat()
    if isinstance(o, uuid.UUID):
        return str(o)
    # Fallback: string
    return str(o)


class JsonFormatter(logging.Formatter):
    ALLOWED = {
        "t",
        "lvl",
        "msg",
        "event",
        "corr",
        "node",
        "tool",
        "model",
        "text",
        "prompts",
        "tokens",
        "inputs",
        "outputs",
        "error",
        "run_id",
        "parent_run_id",
        "tool_call_id",
        "duration_ms",
    }

    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "t": _ts(),
            "lvl": record.levelname,
            "msg": record.getMessage(),
        }
        # LoggerAdapter merges extras into record.__dict__
        for k, v in record.__dict__.items():
            if k in self.ALLOWED and v is not None:
                payload[k] = v
        return json.dumps(payload, ensure_ascii=False, default=_default)


def get_json_logger(name="app", level=logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(level)
    h = logging.StreamHandler(sys.stdout)
    h.setFormatter(JsonFormatter())
    logger.addHandler(h)
    return logger


class JsonLoggerAdapter(logging.LoggerAdapter):
    """Inject default fields (e.g., corr id) into record dict."""

    def process(self, msg, kwargs):
        extra = kwargs.get("extra", {}) or {}
        for k, v in self.extra.items():
            extra.setdefault(k, v)
        kwargs["extra"] = extra
        return msg, kwargs


COMPACT = os.getenv("AUDIT_COMPACT", "1") == "1"  # default ON
MAX_FIELD = int(os.getenv("AUDIT_TRUNC", "260"))


def _trunc(v: Any, n: int = MAX_FIELD) -> str:
    s = v
    try:
        if not isinstance(v, str):
            s = json.dumps(v, default=str) if isinstance(v, (dict, list, tuple)) else str(v)
    except Exception:
        s = str(v)
    return s if len(s) <= n else s[:n] + "…"


def _tokens(resp) -> Dict[str, int]:
    # LC usage_metadata
    meta = getattr(resp, "usage_metadata", None) or {}
    if meta:
        return {
            "in": int(meta.get("input_tokens", 0)),
            "out": int(meta.get("output_tokens", 0)),
            "total": int(meta.get("total_tokens", 0)),
        }
    # Azure/OpenAI response_metadata.token_usage
    rmeta = getattr(resp, "response_metadata", None) or {}
    tu = rmeta.get("token_usage") or {}
    if tu:
        return {
            "in": int(tu.get("prompt_tokens", 0)),
            "out": int(tu.get("completion_tokens", 0)),
            "total": int(tu.get("total_tokens", 0)),
        }
    # OpenAI v2 style
    if "usage" in rmeta:
        u = rmeta["usage"]
        return {
            "in": int(u.get("prompt_tokens", 0)),
            "out": int(u.get("completion_tokens", 0)),
            "total": int(u.get("total_tokens", 0)),
        }
    return {"in": 0, "out": 0, "total": 0}


def _first_text(resp) -> str:
    try:
        gens = getattr(resp, "generations", None)
        if gens and gens[0] and gens[0][0]:
            return _trunc(gens[0][0].text)
    except Exception:
        pass
    return _trunc(getattr(resp, "content", "") or "")


class AuditJSONHandler(BaseCallbackHandler):
    """
    Compact JSON logs with durations and tool inputs/outputs.
    Only logs inner chain events if COMPACT=0.
    """

    def __init__(self, corr_id: str):
        base = get_json_logger("audit")
        self.log = JsonLoggerAdapter(base, {"corr": corr_id})
        self._t0: Dict[str, float] = {}
        self._root_chain: Optional[str] = None  # first chain.start run_id seen

    # timing helpers
    def _start(self, run_id):
        if run_id:
            self._t0[str(run_id)] = time.perf_counter()

    def _end(self, run_id) -> Optional[float]:
        if not run_id:
            return None
        t = self._t0.pop(str(run_id), None)
        return None if t is None else round((time.perf_counter() - t) * 1000.0, 2)

    # --- LLM ---
    def on_llm_start(self, serialized, prompts, **kw):
        self._start(kw.get("run_id"))
        self.log.info(
            "llm.start",
            extra={
                "event": "llm.start",
                "model": (serialized or {}).get("id")
                if isinstance(serialized, dict)
                else str(serialized),
                "prompts": [_trunc(p) for p in prompts],
                "run_id": str(kw.get("run_id") or ""),
                "parent_run_id": str(kw.get("parent_run_id") or ""),
            },
        )

    def on_llm_end(self, response, **kw):
        self.log.info(
            "llm.end",
            extra={
                "event": "llm.end",
                "text": _first_text(response),
                "tokens": _tokens(response),
                "run_id": str(kw.get("run_id") or ""),
                "parent_run_id": str(kw.get("parent_run_id") or ""),
                "duration_ms": self._end(kw.get("run_id")),
            },
        )

    # --- Tools (include input/output) ---
    def on_tool_start(self, serialized, input_str, **kw):
        self._start(kw.get("run_id"))
        name = (
            kw.get("name")
            or (serialized.get("name") if isinstance(serialized, dict) else None)
            or "<unknown>"
        )
        # input_str can be dict or string; log compact JSON
        self.log.info(
            "tool.start",
            extra={
                "event": "tool.start",
                "tool": name,
                "inputs": _trunc(input_str),
                "run_id": str(kw.get("run_id") or ""),
                "parent_run_id": str(kw.get("parent_run_id") or ""),
            },
        )

    def on_tool_end(self, output, **kw):
        name = kw.get("name") or "<unknown>"
        self.log.info(
            "tool.end",
            extra={
                "event": "tool.end",
                "tool": name,
                "outputs": _trunc(output),
                "run_id": str(kw.get("run_id") or ""),
                "parent_run_id": str(kw.get("parent_run_id") or ""),
                "duration_ms": self._end(kw.get("run_id")),
            },
        )

    # --- Chains / Graph ---
    def on_chain_start(self, serialized, inputs, **kw):
        self._start(kw.get("run_id"))
        rid = str(kw.get("run_id") or "")
        if self._root_chain is None:
            self._root_chain = rid
        node = kw.get("name") or ("LangGraph" if self._root_chain == rid else "<node>")
        if COMPACT and rid != self._root_chain:
            return  # suppress inner starts
        self.log.info(
            "chain.start",
            extra={
                "event": "chain.start",
                "node": node,
                "inputs": _trunc(type(inputs)),  # don’t dump state
                "run_id": rid,
                "parent_run_id": str(kw.get("parent_run_id") or ""),
            },
        )

    def on_chain_end(self, outputs, **kw):
        rid = str(kw.get("run_id") or "")
        if COMPACT and rid != self._root_chain:
            return  # suppress inner ends
        self.log.info(
            "chain.end",
            extra={
                "event": "chain.end",
                "node": kw.get("name") or ("LangGraph" if rid == self._root_chain else "<node>"),
                "outputs": _trunc(type(outputs)),  # don’t dump state
                "run_id": rid,
                "parent_run_id": str(kw.get("parent_run_id") or ""),
                "duration_ms": self._end(kw.get("run_id")),
            },
        )
