"""
Configurable setup criteria for any setup.

Load from YAML/JSON files (directory or single file). Criteria are generic
(setup_id, name, version, timeframes, entry, stop, conditions) plus
setup_specific key-value for each setup type.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

try:
    import yaml
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False


@dataclass
class SetupCriteria:
    """Generic criteria for any setup; storage-agnostic."""

    setup_id: str
    name: str = ""
    version: str = "1.0"
    timeframes: List[str] = field(default_factory=list)
    entry: Dict[str, Any] = field(default_factory=dict)
    stop: Dict[str, Any] = field(default_factory=dict)
    targets: List[Dict[str, Any]] = field(default_factory=list)
    conditions: List[Dict[str, Any]] = field(default_factory=list)
    setup_specific: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SetupCriteria":
        return cls(
            setup_id=str(d.get("setup_id", "")),
            name=str(d.get("name", "")),
            version=str(d.get("version", "1.0")),
            timeframes=list(d.get("timeframes", [])),
            entry=dict(d.get("entry", {})),
            stop=dict(d.get("stop", {})),
            targets=list(d.get("targets", [])),
            conditions=list(d.get("conditions", [])),
            setup_specific=dict(d.get("setup_specific", {})),
        )

    def get_specific(self, key: str, default: Any = None) -> Any:
        """Convenience: get a setup_specific value with default."""
        return self.setup_specific.get(key, default)


def _load_file(path: Path) -> Dict[str, Any]:
    suffix = path.suffix.lower()
    text = path.read_text(encoding="utf-8")
    if suffix in (".yaml", ".yml"):
        if not _HAS_YAML:
            raise RuntimeError("YAML support requires PyYAML; install with: pip install pyyaml")
        return yaml.safe_load(text) or {}
    if suffix == ".json":
        return json.loads(text)
    raise ValueError(f"Unsupported format: {suffix}")


def load_criteria(
    path: Union[str, Path],
    *,
    env_key: Optional[str] = None,
) -> Dict[str, SetupCriteria]:
    """
    Load setup criteria from a file or directory. Configurable via path or env.

    - If path is a file: load that file (one setup; setup_id from content).
    - If path is a directory: load all .yaml, .yml, .json files; each file can
      define one setup (setup_id in content) or a list under a key (e.g. setups: [...]).

    If env_key is set and the path is empty, path is taken from environment variable env_key.
    Returns dict mapping setup_id -> SetupCriteria.
    """
    if env_key:
        import os
        path = path or os.environ.get(env_key, path)
    path = Path(path)
    if not path.exists():
        return {}

    result: Dict[str, SetupCriteria] = {}

    if path.is_file():
        data = _load_file(path)
        _add_from_data(data, result)
        return result

    for f in path.iterdir():
        if f.suffix.lower() in (".yaml", ".yml", ".json") and f.is_file():
            try:
                data = _load_file(f)
                _add_from_data(data, result)
            except Exception:
                continue
    return result


def _add_from_data(data: Dict[str, Any], result: Dict[str, SetupCriteria]) -> None:
    """Add one or more setups from parsed data into result."""
    if "setup_id" in data:
        one = SetupCriteria.from_dict(data)
        result[one.setup_id] = one
        return
    if "setups" in data:
        for item in data["setups"]:
            if isinstance(item, dict) and "setup_id" in item:
                one = SetupCriteria.from_dict(item)
                result[one.setup_id] = one
    return


def get_criteria(
    criteria_dir: Union[str, Path, None] = None,
    cache: Optional[Dict[str, SetupCriteria]] = None,
    env_key: str = "SETUP_CRITERIA_DIR",
) -> Dict[str, SetupCriteria]:
    """
    Get all loaded criteria. Configurable source:

    - criteria_dir: explicit path (file or directory).
    - cache: if provided and criteria_dir is None, return cache.
    - env_key: if no criteria_dir, use env var (e.g. SETUP_CRITERIA_DIR).

    Callers can pass cache={} and reuse it after first load.
    """
    if cache is not None and criteria_dir is None:
        return cache
    path = criteria_dir or ""
    return load_criteria(path, env_key=env_key)
