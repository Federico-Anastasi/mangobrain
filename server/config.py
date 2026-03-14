"""MangoBrain — Configuration (TOML + .env + env vars)."""

from __future__ import annotations

import logging
import os
import tomllib
from pathlib import Path

import tiktoken
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# ── Locate project root ──────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ── Load config layers: mangobrain.toml -> .env -> environment ────────────────

def _load_toml() -> dict:
    """Load mangobrain.toml if it exists."""
    toml_path = PROJECT_ROOT / "mangobrain.toml"
    if toml_path.exists():
        with open(toml_path, "rb") as f:
            return tomllib.load(f)
    return {}

_toml = _load_toml()
load_dotenv(PROJECT_ROOT / ".env")


def _get(section: str, key: str, default: str) -> str:
    """Get config value: env var > toml > default."""
    env_key = f"MANGOBRAIN_{section.upper()}_{key.upper()}" if section else key.upper()
    # Also check legacy env var names (without prefix)
    legacy_keys = {
        ("database", "path"): "DB_PATH",
        ("embedding", "model"): "EMBEDDING_MODEL",
        ("embedding", "device"): "EMBEDDING_DEVICE",
        ("server", "api_port"): "API_PORT",
        ("retrieval", "alpha"): "ALPHA",
        ("retrieval", "dedup_threshold"): "DEDUP_THRESHOLD",
        ("retrieval", "deep_budget"): "DEEP_BUDGET",
        ("retrieval", "quick_budget"): "QUICK_BUDGET",
        ("retrieval", "session_quick_budget"): "SESSION_QUICK_BUDGET",
        ("retrieval", "deep_max_results"): "DEEP_MAX_RESULTS",
        ("retrieval", "quick_max_results"): "QUICK_MAX_RESULTS",
        ("retrieval", "deep_threshold"): "RELEVANCE_THRESHOLD_RATIO",
        ("retrieval", "quick_threshold"): "QUICK_RELEVANCE_THRESHOLD_RATIO",
        ("decay", "episodic"): "DECAY_LAMBDA_EPISODIC",
        ("decay", "semantic"): "DECAY_LAMBDA_SEMANTIC",
        ("decay", "procedural"): "DECAY_LAMBDA_PROCEDURAL",
    }

    # 1. Check prefixed env var
    val = os.getenv(env_key)
    if val is not None:
        return val

    # 2. Check legacy env var
    legacy = legacy_keys.get((section, key))
    if legacy:
        val = os.getenv(legacy)
        if val is not None:
            return val

    # 3. Check TOML
    toml_section = _toml.get(section, {})
    if key in toml_section:
        return str(toml_section[key])

    # 4. Default
    return default


# ── Auto-detect GPU ───────────────────────────────────────────────────────────

def _detect_device() -> str:
    """Auto-detect CUDA availability."""
    configured = _get("embedding", "device", "auto")
    if configured != "auto":
        return configured
    try:
        import torch
        if torch.cuda.is_available():
            logger.info("CUDA detected — using GPU for embeddings")
            return "cuda"
    except ImportError:
        pass
    logger.info("No CUDA — using CPU for embeddings")
    return "cpu"


def _resolve_model(device: str) -> str:
    """Resolve embedding model based on device."""
    configured = _get("embedding", "model", "auto")
    if configured != "auto":
        return configured
    if device == "cuda":
        return "BAAI/bge-large-en-v1.5"   # 1024 dim, best quality
    return "BAAI/bge-base-en-v1.5"         # 768 dim, good on CPU


# ── Resolved config values ────────────────────────────────────────────────────

# Paths
DB_PATH = PROJECT_ROOT / _get("database", "path", "data/mangobrain.db")

# Embedding
EMBEDDING_DEVICE = _detect_device()
EMBEDDING_MODEL = _resolve_model(EMBEDDING_DEVICE)

# Server
API_PORT = int(_get("server", "api_port", "3101"))

# Retrieval
ALPHA = float(_get("retrieval", "alpha", "0.3"))
DEDUP_THRESHOLD = float(_get("retrieval", "dedup_threshold", "0.92"))
DEEP_BUDGET = int(_get("retrieval", "deep_budget", "8000"))
QUICK_BUDGET = int(_get("retrieval", "quick_budget", "2000"))
SESSION_QUICK_BUDGET = int(_get("retrieval", "session_quick_budget", "4000"))
DEEP_MAX_RESULTS = int(_get("retrieval", "deep_max_results", "20"))
QUICK_MAX_RESULTS = int(_get("retrieval", "quick_max_results", "6"))
RELEVANCE_THRESHOLD_RATIO = float(_get("retrieval", "deep_threshold", "0.78"))
QUICK_RELEVANCE_THRESHOLD_RATIO = float(_get("retrieval", "quick_threshold", "0.85"))

# Decay
DECAY_LAMBDA_EPISODIC = float(_get("decay", "episodic", "0.01"))
DECAY_LAMBDA_SEMANTIC = float(_get("decay", "semantic", "0.002"))
DECAY_LAMBDA_PROCEDURAL = float(_get("decay", "procedural", "0.001"))

DECAY_LAMBDAS = {
    "episodic": DECAY_LAMBDA_EPISODIC,
    "semantic": DECAY_LAMBDA_SEMANTIC,
    "procedural": DECAY_LAMBDA_PROCEDURAL,
}

# ── Token counting ────────────────────────────────────────────────────────────

_encoder = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    """Count tokens using cl100k_base encoding."""
    return len(_encoder.encode(text))
