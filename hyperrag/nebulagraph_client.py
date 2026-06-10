from dataclasses import dataclass, field
from typing import Protocol, Sequence


class NebulaGraphClient(Protocol):
    def execute(self, statement: str) -> object:
        ...

    def is_available(self) -> bool:
        ...


@dataclass
class FakeNebulaGraphClient:
    statements: list[str] = field(default_factory=list)
    available: bool = True

    def execute(self, statement: str) -> object:
        self.statements.append(statement)
        return []

    def execute_many(self, statements: Sequence[str]) -> list[object]:
        return [self.execute(statement) for statement in statements]

    def is_available(self) -> bool:
        return self.available
