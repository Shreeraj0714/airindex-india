from abc import ABC, abstractmethod


class BaseCollector(ABC):
    """Implement this for authorized APIs, user CSVs, or permitted public data."""

    @abstractmethod
    def collect(self) -> list[dict]: ...

    @abstractmethod
    def validate(self, item: dict) -> tuple[str, list[str]]: ...

    @abstractmethod
    def normalize(self, item: dict) -> dict: ...
