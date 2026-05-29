"""Registry[T] - the generic plugin registry used throughout Duecare."""

from __future__ import annotations

from typing import Callable, Generic, Iterator, TypeVar

T = TypeVar("T")


class Registry(Generic[T]):
    """A named registry of plugin instances (or classes).

    Every plugin kind (models, domains, agents, tasks) has its own Registry
    instance but shares this code. Plugins register themselves on import via
    @registry.register("id").
    """

    def __init__(self, kind: str) -> None:
        self.kind = kind
        self._by_id: dict[str, T] = {}
        self._metadata: dict[str, dict] = {}

    def register(
        self,
        id: str,
        **metadata,
    ) -> Callable[[T], T]:
        """Decorator to register a plugin under `id`."""
        def decorator(cls_or_instance: T) -> T:
            if id in self._by_id:
                if self._same_registration(self._by_id[id], cls_or_instance):
                    return cls_or_instance
                raise ValueError(
                    f"{self.kind} id {id!r} is already registered"
                )
            self._by_id[id] = cls_or_instance
            self._metadata[id] = metadata
            return cls_or_instance
        return decorator

    def add(self, id: str, entry: T, **metadata) -> None:
        """Imperative registration (outside of class-decoration flow)."""
        if id in self._by_id:
            if self._same_registration(self._by_id[id], entry):
                return
            raise ValueError(f"{self.kind} id {id!r} is already registered")
        self._by_id[id] = entry
        self._metadata[id] = metadata

    @staticmethod
    def _same_registration(existing: T, candidate: T) -> bool:
        """Treat repeated imports of the same plugin as idempotent.

        Pytest importlib mode and editable namespace-package installs can
        execute a plugin module more than once during collection. That should
        not make package import fail. A genuinely different plugin trying to
        claim the same id still raises.
        """
        if existing is candidate:
            return True

        existing_obj = existing if isinstance(existing, type) else type(existing)
        candidate_obj = candidate if isinstance(candidate, type) else type(candidate)
        if (
            getattr(existing_obj, "__module__", None),
            getattr(existing_obj, "__qualname__", None),
        ) == (
            getattr(candidate_obj, "__module__", None),
            getattr(candidate_obj, "__qualname__", None),
        ):
            return True

        # Fall back to a __qualname__-only match. This IS load-bearing: under
        # pytest importlib mode (and editable namespace installs) a plugin
        # module is re-exec'd during full-suite collection under a DIFFERENT
        # __module__, so the (__module__, __qualname__) pair above misses the
        # re-import and `add()` would raise "id already registered", breaking
        # collection of the whole suite. Qualname-only keeps the re-import
        # idempotent. (Trade-off: two genuinely DIFFERENT plugins that share a
        # class name across modules would be treated as the same here — but no
        # in-tree plugin does that, and breaking full-suite collection is the
        # worse failure. A 2026-05-28 attempt to `return False` here regressed
        # the full suite; do not remove this branch without a real cross-module
        # qualname-collision test proving it is safe.)
        return getattr(existing_obj, "__qualname__", None) == getattr(
            candidate_obj, "__qualname__", None
        )

    def get(self, id: str) -> T:
        if id not in self._by_id:
            known = ", ".join(sorted(self._by_id.keys())) or "(empty)"
            raise KeyError(
                f"Unknown {self.kind} id {id!r}. Known: {known}"
            )
        return self._by_id[id]

    def has(self, id: str) -> bool:
        return id in self._by_id

    def all_ids(self) -> list[str]:
        return sorted(self._by_id.keys())

    def metadata(self, id: str) -> dict:
        return self._metadata.get(id, {})

    def items(self) -> Iterator[tuple[str, T]]:
        for id in self.all_ids():
            yield id, self._by_id[id]

    def __len__(self) -> int:
        return len(self._by_id)

    def __contains__(self, id: str) -> bool:
        return id in self._by_id

    def __repr__(self) -> str:
        return f"Registry[{self.kind}]({len(self)} entries)"
