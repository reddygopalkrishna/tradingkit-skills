"""Broker adapters. All share the Broker interface in base.py."""

from __future__ import annotations

from typing import Optional

from .. import config
from .base import Broker, BrokerError  # noqa: F401


def get_broker(name: Optional[str] = None) -> Broker:
    name = (name or config.load()["broker"]["name"] or "paper").lower()
    if name == "paper":
        from .paper import PaperBroker
        return PaperBroker()
    if name == "kite":
        from .kite import KiteBroker
        return KiteBroker()
    raise BrokerError(f"unknown broker {name!r} (paper | kite)")
