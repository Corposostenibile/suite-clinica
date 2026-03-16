"""Compat wrapper per il parser pacchetto della vecchia suite."""

from corposostenibile.package_support import parse_package_support


def parse_package_name(name: str) -> dict:
    """Mantiene l'API legacy riutilizzando il parser condiviso."""
    return parse_package_support(name)
