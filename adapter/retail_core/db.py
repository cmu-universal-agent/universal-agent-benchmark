"""Seed loading, per-run isolation, and deterministic reset for the retail
simulator. No framework code, no randomness, no wall-clock reads -- every
source of variation is driven off the fixed seed data plus a per-run
monotonic counter that restarts at zero on every reset(), so two resets of
the same case always produce byte-identical state.
"""

import copy
import json
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_seed(data_dir: Path) -> dict[str, dict[str, Any]]:
    return {
        "users": _load_json(data_dir / "users.json"),
        "orders": _load_json(data_dir / "orders.json"),
        "products": _load_json(data_dir / "products.json"),
    }


class RetailDB:
    """Owns the mutable world state for a single run. Never share an
    instance -- or its .users/.orders/.products dicts -- across runs."""

    def __init__(self, data_dir: Path) -> None:
        self._seed = load_seed(data_dir)
        self.users: dict[str, Any] = {}
        self.orders: dict[str, Any] = {}
        self.products: dict[str, Any] = {}
        self._ledger: set[tuple] = set()
        self._id_counter = 0
        self.reset()

    def reset(self) -> None:
        fresh = copy.deepcopy(self._seed)
        self.users = fresh["users"]
        self.orders = fresh["orders"]
        self.products = fresh["products"]
        self._ledger = set()
        self._id_counter = 0

    # -- reads --------------------------------------------------------

    def get_user(self, user_id: str) -> dict[str, Any] | None:
        return self.users.get(user_id)

    def get_order(self, order_id: str) -> dict[str, Any] | None:
        return self.orders.get(order_id)

    def get_product(self, product_id: str) -> dict[str, Any] | None:
        return self.products.get(product_id)

    # -- idempotency ledger --------------------------------------------

    def already_applied(self, key: tuple) -> bool:
        return key in self._ledger

    def mark_applied(self, key: tuple) -> None:
        self._ledger.add(key)

    def next_id(self, prefix: str) -> str:
        self._id_counter += 1
        return f"{prefix}{self._id_counter:04d}"

    # -- mutations (called only after tools.py has validated the request) --

    def apply_refund(self, order: dict[str, Any], amount: float) -> None:
        order["refunded_amount"] = round(order["refunded_amount"] + amount, 2)
        order["status"] = "refunded"

    def apply_exchange(self, order: dict[str, Any], old_item_id: str, new_item_id: str, new_price: float) -> None:
        for item in order["items"]:
            if item["item_id"] == old_item_id:
                item["item_id"] = new_item_id
                item["price"] = new_price
        order.setdefault("exchange_history", []).append({"from": old_item_id, "to": new_item_id})
        order["status"] = "exchanged"

    def apply_return(self, order: dict[str, Any], item_id: str) -> None:
        order.setdefault("returned_items", []).append(item_id)
        order["status"] = "returned"

    def apply_escalation(self, order: dict[str, Any], reason: str) -> str:
        ticket_id = self.next_id("ESC-")
        order.setdefault("escalations", []).append({"ticket_id": ticket_id, "reason": reason})
        return ticket_id
