from __future__ import annotations
from typing import Any, Iterator, Type, TypeVar

T = TypeVar("T")


class World:
    def __init__(self) -> None:
        self._next_id: int = 0
        self._components: dict[type, dict[int, Any]] = {}
        self._alive: set[int] = set()
        self._dead: set[int] = set()

    def create_entity(self, *components: Any) -> int:
        eid = self._next_id
        self._next_id += 1
        self._alive.add(eid)
        for c in components:
            self.add_component(eid, c)
        return eid

    def add_component(self, entity: int, component: Any) -> None:
        ctype = type(component)
        if ctype not in self._components:
            self._components[ctype] = {}
        self._components[ctype][entity] = component

    def remove_component(self, entity: int, ctype: type) -> None:
        self._components.get(ctype, {}).pop(entity, None)

    def get(self, entity: int, ctype: Type[T]) -> T | None:
        return self._components.get(ctype, {}).get(entity)

    def has(self, entity: int, *ctypes: type) -> bool:
        return all(entity in self._components.get(ct, {}) for ct in ctypes)

    def query(self, *ctypes: type) -> Iterator[tuple[int, tuple]]:
        if not ctypes:
            return
        stores = [self._components.get(ct, {}) for ct in ctypes]
        smallest = min(stores, key=len)
        for eid in list(smallest):
            if eid in self._alive and all(eid in s for s in stores):
                yield eid, tuple(s[eid] for s in stores)

    def query1(self, ctype: Type[T]) -> Iterator[tuple[int, T]]:
        store = self._components.get(ctype, {})
        for eid, comp in list(store.items()):
            if eid in self._alive:
                yield eid, comp

    def delete_entity(self, entity: int) -> None:
        self._alive.discard(entity)
        self._dead.add(entity)

    def flush_dead(self) -> None:
        for eid in self._dead:
            for store in self._components.values():
                store.pop(eid, None)
        self._dead.clear()

    @property
    def entities(self) -> frozenset[int]:
        return frozenset(self._alive)
