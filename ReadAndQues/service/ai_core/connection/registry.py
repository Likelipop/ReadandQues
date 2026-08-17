from collections.abc import Callable
from typing import Any

ModelFactory = Callable[[float], Any]

_PROVIDERS: dict[str, ModelFactory] = {}


def register_provider(name: str) -> Callable[[ModelFactory], ModelFactory]:
    def decorator(func: ModelFactory) -> ModelFactory:
        _PROVIDERS[name] = func
        return func

    return decorator


def get_provider(name: str) -> ModelFactory:
    if name not in _PROVIDERS:
        raise ValueError(f"Provider '{name}' not found.")
    return _PROVIDERS[name]


def get_all_providers() -> dict[str, ModelFactory]:
    return _PROVIDERS
