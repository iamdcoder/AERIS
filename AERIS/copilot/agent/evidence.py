from typing import Any

from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    evidence_id: str

    kind: str

    title: str

    summary: str

    source: str

    candidate_id: str | None = None

    severity: str | None = None

    data: dict[str, Any] = Field(
        default_factory=dict
    )


class EvidenceStore:
    def __init__(self) -> None:
        self._items: list[
            EvidenceItem
        ] = []

    def reset(self) -> None:
        self._items = []

    def add(
        self,
        *,
        kind: str,
        title: str,
        summary: str,
        source: str,
        candidate_id: str | None = None,
        severity: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> EvidenceItem:
        evidence_id = (
            f"E{len(self._items) + 1:03d}"
        )

        item = EvidenceItem(
            evidence_id=evidence_id,
            kind=kind,
            title=title,
            summary=summary,
            source=source,
            candidate_id=candidate_id,
            severity=severity,
            data=data or {},
        )

        self._items.append(
            item
        )

        return item

    def get(
        self,
        evidence_id: str,
    ) -> EvidenceItem | None:
        for item in self._items:
            if (
                item.evidence_id
                == evidence_id
            ):
                return item

        return None

    def all(
        self,
    ) -> list[EvidenceItem]:
        return list(
            self._items
        )

    def ids(
        self,
    ) -> list[str]:
        return [
            item.evidence_id
            for item in self._items
        ]

    def as_dicts(
        self,
    ) -> list[dict[str, Any]]:
        return [
            item.model_dump()
            for item
            in self._items
        ]