"""SchemaRegistry: indexes contracts as plain pydantic models -- Python
objects, not JSON files -- by name, built once per session. Every *.py
module under api_schema_dir that exports a module-level `SCHEMAS` dict
contributes its {name: model} pairs; a name can map to a BaseModel
subclass (a single object) or any pydantic-compatible type (e.g.
list[SomeModel], for a list-shaped response) -- both are validated the
same way via TypeAdapter. Converts a validation failure into the same
short field-level problem list the report renders, whether the failure is
a missing required field or an unexpected extra one (models declare
`model_config = ConfigDict(extra="forbid")` to flag drift).
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter, ValidationError

from core.errors import ConfigError

_MODULE_GLOB = "*.py"


class SchemaRegistry:
    """Built once per session (see core.plugin.pytest_configure)."""

    def __init__(self, schema_dir: Path):
        self._schema_dir = schema_dir
        self._by_name: dict[str, Any] = {}
        self._adapters: dict[str, TypeAdapter] = {}
        self._index()

    @property
    def names(self) -> list[str]:
        return sorted(self._by_name)

    def validate(self, name: str, instance: Any) -> list[dict]:
        """Returns [] if instance matches the schema, else a field-level
        problem list: [{"path": "$.email", "problem": "..."}, ...]."""
        adapter = self._adapter_for(name)
        try:
            adapter.validate_python(instance)
        except ValidationError as exc:
            return [{"path": _format_loc(e["loc"]), "problem": e["msg"]} for e in exc.errors()]
        return []

    # -- internals ------------------------------------------------------

    def _index(self) -> None:
        if not self._schema_dir.exists():
            return
        for path in sorted(self._schema_dir.rglob(_MODULE_GLOB)):
            if path.name == "__init__.py":
                continue
            module = self._load_module(path)
            schemas = getattr(module, "SCHEMAS", None)
            if not schemas:
                continue
            for name, model in schemas.items():
                if name in self._by_name:
                    raise ConfigError(
                        f"duplicate schema name {name!r}: already registered before {path} -- "
                        f"give one of them a distinct SCHEMAS key"
                    )
                self._by_name[name] = model

    def _load_module(self, path: Path):
        # unique module name so two files with the same stem (e.g.
        # users.py under different subfolders) never collide in sys.modules
        module_name = f"_api_schema__{path.stem}__{abs(hash(str(path.resolve())))}"
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            raise ConfigError(f"could not load schema module {path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module

    def _adapter_for(self, name: str) -> TypeAdapter:
        if name in self._adapters:
            return self._adapters[name]
        if name not in self._by_name:
            raise ConfigError(
                f"no schema named {name!r} indexed from {self._schema_dir}. "
                f"Available: {self.names or 'none'}"
            )
        adapter = TypeAdapter(self._by_name[name])
        self._adapters[name] = adapter
        return adapter


def _format_loc(loc: tuple) -> str:
    path = "$"
    for part in loc:
        path += f"[{part}]" if isinstance(part, int) else f".{part}"
    return path


# -- session-scoped singleton, configured once by core.plugin -----------
#
# assert_schema() (core.assertions) needs a registry without every call
# site threading Settings/SchemaRegistry through it -- same shape as
# core.recorder's "active recorder" contextvar, except this one is a
# single object for the whole session (not per-test), so a plain module
# global is enough; no context binding needed.
_registry: SchemaRegistry | None = None


def configure(schema_dir: Path) -> SchemaRegistry:
    global _registry
    _registry = SchemaRegistry(schema_dir)
    return _registry


def get_registry() -> SchemaRegistry:
    if _registry is None:
        raise ConfigError(
            "SchemaRegistry not configured -- core.plugin.pytest_configure "
            "should call core.schemas.configure(settings.api_schema_dir) at session start"
        )
    return _registry
