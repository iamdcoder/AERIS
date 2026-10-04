from typing import Any

from pydantic import BaseModel, Field


class MemoryEntry(BaseModel):
    memory_id: str

    category: str

    content: str

    source: str

    importance: str = "MEDIUM"

    data: dict[str, Any] = Field(
        default_factory=dict
    )


class AgentMemory:
    """
    Compact structured working memory.

    This is intentionally not a raw LLM transcript.

    Memory contains observable operational facts, tool outcomes
    and evidence summaries that can safely be reused by later
    agent stages.
    """

    def __init__(self) -> None:
        self._entries: list[
            MemoryEntry
        ] = []

    def remember(
        self,
        *,
        category: str,
        content: str,
        source: str,
        importance: str = "MEDIUM",
        data: dict[str, Any] | None = None,
    ) -> MemoryEntry:
        memory_id = (
            f"M{len(self._entries) + 1:03d}"
        )

        entry = MemoryEntry(
            memory_id=memory_id,
            category=category,
            content=content,
            source=source,
            importance=importance,
            data=data or {},
        )

        self._entries.append(
            entry
        )

        return entry

    def get(
        self,
        memory_id: str,
    ) -> MemoryEntry | None:
        for entry in self._entries:
            if (
                entry.memory_id
                == memory_id
            ):
                return entry

        return None

    def all(
        self,
    ) -> list[MemoryEntry]:
        return list(
            self._entries
        )

    def by_category(
        self,
        category: str,
    ) -> list[MemoryEntry]:
        return [
            entry
            for entry
            in self._entries
            if entry.category
            == category
        ]

    def as_dicts(
        self,
    ) -> list[dict[str, Any]]:
        return [
            entry.model_dump()
            for entry
            in self._entries
        ]