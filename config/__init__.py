# config/__init__.py
"""Пакет конфигурации."""

from .settings import load_config, AppConfig

__all__ = ["load_config", "AppConfig"]