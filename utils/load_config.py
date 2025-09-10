"""
Generic configuration loading utilities.
"""
from __future__ import annotations

from pathlib import Path
import configparser
import os
import logging
from types import SimpleNamespace
from typing import Optional, Dict, Any

CONFIG_PATH = Path(__file__).parent.parent / "config.ini"
_RAW_CONFIG: Optional[configparser.ConfigParser] = None

# Mapping: config.ini key -> (attribute name, type, required)
_FIELD_SPECS = [
    ("dataset_id", "DATASET_ID", str, True),
    ("congress_csv_name", "CONGRESS_CSV_NAME", str, True),
    ("stock_prices_csv_name", "STOCK_PRICES_CSV_NAME", str, True),
    ("output_csv", "OUTPUT_CSV", str, True),
    ("filter_start", "FILTER_START", str, True),
    ("filter_end", "FILTER_END", str, True),
    ("max_transactions_per_politician", "MAX_TRANSACTIONS_PER_POLITICIAN", int, True),
    ("max_rows", "MAX_ROWS_TO_PROCESS", int, False),
    ("prompt_col", "PROMPT_COL", str, True),
    ("response_col", "RESPONSE_COL", str, True),
    ("model_name", "MODEL_NAME", str, True),
    ("rate_limit_seconds", "RATE_LIMIT_SECONDS", float, False),
    ("api_key", "API_KEY", str, False),
    ("dry_run", "DRY_RUN", bool, False),
    ("overwrite_existing", "OVERWRITE_EXISTING_RESPONSES", bool, False),
    ("intermediate_save_every", "INTERMEDIATE_SAVE_EVERY", int, False),
    ("max_workers", "MAX_WORKERS", int, False),
    ("log_level", "LOG_LEVEL", str, False),
]

_FIELD_SPECS_POLITICIAN_NETWORK = [
    ("transactions_csv", "TRANSACTIONS_CSV", str, True),
    ("profiles_out", "PROFILES_OUT", str, True),
    ("collaborations_out", "COLLABORATIONS_OUT", str, True),
    ("dry_run", "DRY_RUN", bool, False),
    ("overwrite", "OVERWRITE", bool, False),
    ("max_profiles", "MAX_PROFILES", int, False),
    ("max_pairs", "MAX_PAIRS", int, False),
    ("max_workers", "MAX_WORKERS", int, False),
    ("intermediate_every", "INTERMEDIATE_EVERY", int, False),
    ("model_name", "MODEL_NAME", str, False),
    ("log_level", "LOG_LEVEL", str, False),
]

_BOOL_TRUE = {"1", "true", "yes", "y", "on"}


def load_config(reload: bool = False) -> configparser.ConfigParser:
    global _RAW_CONFIG
    if _RAW_CONFIG is not None and not reload:
        return _RAW_CONFIG
    parser = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())
    if CONFIG_PATH.exists():
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        parser["DEFAULT"] = {"project_dir": str(project_root)}
        parser.read(CONFIG_PATH)
    else:
        logging.warning("config.ini not found at %s; proceeding with empty parser", CONFIG_PATH)
    _RAW_CONFIG = parser
    return parser


def _coerce_bool(val: str) -> bool:
    return str(val).strip().lower() in _BOOL_TRUE


def _coerce_log_level(value: str, default: int = logging.INFO) -> int:
    if not value:
        return default
    value = value.strip()
    if value.isdigit():
        return int(value)
    return getattr(logging, value.upper(), default)


def load_transactions_config(reload: bool = False) -> SimpleNamespace:
    parser = load_config(reload=reload)
    section = "create_transactions_dataset"
    if not parser.has_section(section):
        raise ValueError(f"Missing [{section}] section in config.ini")

    data_raw: Dict[str, Any] = dict(parser.items(section))

    missing_required = [
        cfg_key for cfg_key, _, _, req in _FIELD_SPECS if req and cfg_key not in data_raw
    ]
    if missing_required:
        raise ValueError(f"Missing required config keys in [{section}]: {', '.join(missing_required)}")

    coercers = {int: int, float: float, bool: _coerce_bool, str: str}
    ns_dict: Dict[str, Any] = {}
    for cfg_key, attr, tp, _ in _FIELD_SPECS:
        raw = data_raw.get(cfg_key)
        if raw is None:
            continue
        try:
            ns_dict[attr] = coercers[tp](raw)
        except (TypeError, ValueError, KeyError):
            raise ValueError(f"Invalid value for {cfg_key}: {raw}") from None

    # Set defaults for optional values if not present in config
    ns_dict.setdefault("MAX_ROWS_TO_PROCESS", None)
    ns_dict.setdefault("RATE_LIMIT_SECONDS", 1.2)
    ns_dict.setdefault("API_KEY", "")
    ns_dict.setdefault("DRY_RUN", False)
    ns_dict.setdefault("OVERWRITE_EXISTING_RESPONSES", False)
    ns_dict.setdefault("INTERMEDIATE_SAVE_EVERY", 5)
    ns_dict.setdefault("MAX_WORKERS", 4)
    ns_dict.setdefault("LOG_LEVEL", logging.INFO)

    # Environment overrides
    if env_api := os.getenv("GEMINI_API_KEY", "").strip():
        ns_dict["API_KEY"] = env_api
    if env_model := os.getenv("MODEL_NAME", "").strip():
        ns_dict["MODEL_NAME"] = env_model
    if env_max_rows := os.getenv("MAX_ROWS_TO_PROCESS", "").strip():
        if env_max_rows.isdigit():
            v = int(env_max_rows)
            ns_dict["MAX_ROWS_TO_PROCESS"] = v if v > 0 else None
    if env_log := os.getenv("LOG_LEVEL", "").strip():
        ns_dict["LOG_LEVEL"] = _coerce_log_level(env_log, ns_dict["LOG_LEVEL"])

    # Post-processing and normalization
    if ns_dict.get("MAX_ROWS_TO_PROCESS") is not None:
        ns_dict["MAX_ROWS_TO_PROCESS"] = int(ns_dict["MAX_ROWS_TO_PROCESS"])

    if isinstance(ns_dict.get("LOG_LEVEL"), str):
        ns_dict["LOG_LEVEL"] = _coerce_log_level(ns_dict["LOG_LEVEL"], logging.INFO)

    if out_csv := ns_dict.get("OUTPUT_CSV"):
        if not Path(out_csv).is_absolute():
            ns_dict["OUTPUT_CSV"] = str(Path(out_csv))

    return SimpleNamespace(**ns_dict)


def load_politician_network_config(reload: bool = False) -> SimpleNamespace:
    parser = load_config(reload=reload)
    section = "politician_network"
    if not parser.has_section(section):
        raise ValueError(f"Missing [{section}] section in config.ini")

    data_raw: Dict[str, Any] = dict(parser.items(section))

    # Fallbacks from [common]
    common = parser["common"] if parser.has_section("common") else {}

    coercers = {int: int, float: float, bool: _coerce_bool, str: str}
    ns_dict: Dict[str, Any] = {}

    missing_required = [
        cfg_key
        for cfg_key, _, _, req in _FIELD_SPECS_POLITICIAN_NETWORK
        if req and cfg_key not in data_raw
    ]
    if missing_required:
        raise ValueError(
            f"Missing required config keys in [{section}]: {', '.join(missing_required)}"
        )

    for cfg_key, attr, tp, _ in _FIELD_SPECS_POLITICIAN_NETWORK:
        raw = data_raw.get(cfg_key)
        if (raw is None or raw == "") and cfg_key in {"model_name", "log_level"}:
            raw = common.get(cfg_key, None)
        if raw is None or raw == "":
            continue
        try:
            ns_dict[attr] = coercers[tp](raw)
        except (TypeError, ValueError, KeyError):
            raise ValueError(f"Invalid value for {cfg_key}: {raw}") from None

    # Defaults
    ns_dict.setdefault("DRY_RUN", False)
    ns_dict.setdefault("OVERWRITE", False)
    ns_dict.setdefault("MAX_PROFILES", None)
    ns_dict.setdefault("MAX_PAIRS", None)
    ns_dict.setdefault("MAX_WORKERS", 4)
    ns_dict.setdefault("INTERMEDIATE_EVERY", 10)
    ns_dict.setdefault("MODEL_NAME", common.get("model_name", "gemini-2.0-flash"))
    ns_dict.setdefault("LOG_LEVEL", _coerce_log_level(common.get("log_level", "INFO")))

    # Environment overrides
    if env_model := os.getenv("MODEL_NAME", "").strip():
        ns_dict["MODEL_NAME"] = env_model
    if env_log := os.getenv("LOG_LEVEL", "").strip():
        ns_dict["LOG_LEVEL"] = _coerce_log_level(env_log, ns_dict["LOG_LEVEL"])

    # Normalize paths
    for key in ["TRANSACTIONS_CSV", "PROFILES_OUT", "COLLABORATIONS_OUT"]:
        p = ns_dict.get(key)
        if p and not Path(p).is_absolute():
            ns_dict[key] = str(Path(p))

    return SimpleNamespace(**ns_dict)


def get_api_key(service: str = "gemini") -> str:
    service_upper = service.upper()
    key = os.getenv(f"{service_upper}_API_KEY", "").strip()
    if not key and service_upper != "GEMINI":
        key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        parser = load_config()
        # Check specific service section first
        if parser.has_section(service):
            key = parser.get(service, "api_key", fallback="").strip()
        # Then common
        if not key and parser.has_section("common"):
            key = parser.get("common", "api_key", fallback="").strip()
        # Then legacy create_transactions_dataset
        if not key and parser.has_section("create_transactions_dataset"):
            key = parser.get("create_transactions_dataset", "api_key", fallback="").strip()
    if not key:
        raise RuntimeError(
            f"{service.capitalize()} API key not set. Provide via env {service_upper}_API_KEY or GEMINI_API_KEY, or config.ini sections."  # noqa
        )
    return key

__all__ = [
    "load_config",
    "load_transactions_config",
    "load_politician_network_config",
    "get_api_key",
]
