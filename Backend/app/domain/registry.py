from __future__ import annotations

import uuid

from app.domain.edge_types import EDGE_TYPES, EdgeTypeDef


class EdgeTypeRegistry:
    def __init__(self, edge_types: list[EdgeTypeDef] | None = None) -> None:
        self._edge_types = edge_types or EDGE_TYPES
        self._by_id: dict[uuid.UUID, EdgeTypeDef] = {et.id: et for et in self._edge_types}
        self._by_code: dict[str, EdgeTypeDef] = {et.code: et for et in self._edge_types}

    def all(self) -> list[EdgeTypeDef]:
        return list(self._edge_types)

    def get_by_id(self, edge_type_id: uuid.UUID) -> EdgeTypeDef | None:
        return self._by_id.get(edge_type_id)

    def get_by_code(self, code: str) -> EdgeTypeDef | None:
        return self._by_code.get(code)

    def codes_for_ids(self, ids: list[uuid.UUID]) -> list[str]:
        codes: list[str] = []
        for edge_type_id in ids:
            et = self.get_by_id(edge_type_id)
            if et is not None:
                codes.append(et.code)
        return codes

    def ids_for_codes(self, codes: list[str]) -> list[uuid.UUID]:
        ids: list[uuid.UUID] = []
        for code in codes:
            et = self.get_by_code(code)
            if et is not None:
                ids.append(et.id)
        return ids

    def filter_codes(self, *, include_granular: bool) -> list[str]:
        if include_granular:
            return [et.code for et in self._edge_types]
        return [et.code for et in self._edge_types if not et.is_granular]


edge_type_registry = EdgeTypeRegistry()

