"""Seed loading, per-run isolation, and deterministic reset for the retail
simulator. No framework code, no randomness, no wall-clock reads -- every
source of variation is driven off the fixed seed data plus a per-run
monotonic counter that restarts at zero on every reset(), so two resets of
the same case always produce byte-identical state.

Also owns the bounded state evidence required by
schemas/tau_retail_state_record.schema.json (state_sha256 + entity_counts +
mutation_count) -- callers must never serialize .users/.orders/.products
directly into anything evaluator- or agent-facing; use state_record().
"""

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "0.1.0"


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
        self._injected_failures: dict[tuple, str] = {}
        self._id_counter = 0
        self.mutation_count = 0
        self.reset()

    def reset(self) -> None:
        fresh = copy.deepcopy(self._seed)
        self.users = fresh["users"]
        self.orders = fresh["orders"]
        self.products = fresh["products"]
        self._ledger = set()
        self._injected_failures = {}
        self._id_counter = 0
        self.mutation_count = 0

    # -- bounded state evidence ----------------------------------------

    def state_sha256(self) -> str:
        canonical = json.dumps(
            {"users": self.users, "orders": self.orders, "products": self.products},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()

    def entity_counts(self) -> dict[str, int]:
        return {
            "orders": len(self.orders),
            "products": len(self.products),
            "users": len(self.users),
        }

    def state_record(self, *, reset_id: str, case_id: str, sequence_index: int) -> dict[str, Any]:
        """A tau_retail_state_record.schema.json-conformant snapshot."""
        return {
            "contract_version": CONTRACT_VERSION,
            "reset_id": reset_id,
            "case_id": case_id,
            "sequence_index": sequence_index,
            "state_sha256": self.state_sha256(),
            "entity_counts": self.entity_counts(),
            "mutation_count": self.mutation_count,
        }

    def record_mutation(self) -> None:
        self.mutation_count += 1

    # -- reads --------------------------------------------------------

    def get_user(self, user_id: str) -> dict[str, Any] | None:
        return self.users.get(user_id)

    def get_order(self, order_id: str) -> dict[str, Any] | None:
        return self.orders.get(order_id)

    def get_product(self, product_id: str) -> dict[str, Any] | None:
        return self.products.get(product_id)

    def find_item(self, item_id: str) -> tuple[dict[str, Any], dict[str, Any]] | None:
        """Return (product, variant) for a catalog item_id, or None."""
        for product in self.products.values():
            for variant in product["variants"]:
                if variant["item_id"] == item_id:
                    return product, variant
        return None

    def find_user_id_by_email(self, email: str) -> str | None:
        for user in self.users.values():
            if user.get("email", "").lower() == email.lower():
                return user["user_id"]
        return None

    def find_user_id_by_name_zip(self, first_name: str, last_name: str, zip_code: str) -> str | None:
        for user in self.users.values():
            if (
                user.get("first_name", "").lower() == first_name.lower()
                and user.get("last_name", "").lower() == last_name.lower()
                and user.get("zip") == zip_code
            ):
                return user["user_id"]
        return None

    # -- idempotency ledger --------------------------------------------

    def already_applied(self, key: tuple) -> bool:
        return key in self._ledger

    def mark_applied(self, key: tuple) -> None:
        self._ledger.add(key)

    def next_id(self, prefix: str) -> str:
        self._id_counter += 1
        return f"{prefix}{self._id_counter:04d}"

    # -- injected failures (offline fixture use only) -------------------
    #
    # Reset clears these (WS3 contract lifecycle rule #2). A failure fires
    # exactly once so a same-arguments retry after a tool_failure succeeds,
    # matching the contract's minimum tool_failure/recovery fixture.

    def inject_failure(self, key: tuple, error_type: str) -> None:
        self._injected_failures[key] = error_type

    def pop_injected_failure(self, key: tuple) -> str | None:
        return self._injected_failures.pop(key, None)

    # -- mutations (called only after tools.py has validated the request) --

    def apply_cancel_pending_order(self, order: dict[str, Any], reason: str) -> None:
        order["status"] = "cancelled"
        order["cancel_reason"] = reason
        order.setdefault("payment_history", []).append(
            {"transaction_type": "refund", "amount": order["total"]}
        )
        self.record_mutation()

    def apply_exchange_delivered_order_items(
        self,
        order: dict[str, Any],
        item_ids: list[str],
        new_item_ids: list[str],
        payment_method_id: str,
        price_delta: float,
    ) -> None:
        by_old_id = dict(zip(item_ids, new_item_ids))
        for item in order["items"]:
            if item["item_id"] in by_old_id:
                new_item_id = by_old_id[item["item_id"]]
                _, variant = self.find_item(new_item_id)
                item["item_id"] = new_item_id
                item["price"] = variant["price"]
        order["status"] = "exchange_requested"
        order.setdefault("payment_history", []).append(
            {
                "transaction_type": "adjustment",
                "amount": price_delta,
                "payment_method_id": payment_method_id,
            }
        )
        self.record_mutation()

    def apply_return_delivered_order_items(
        self, order: dict[str, Any], item_ids: list[str], payment_method_id: str, refund_amount: float
    ) -> None:
        order.setdefault("returned_items", []).extend(item_ids)
        order["status"] = "return_requested"
        order.setdefault("payment_history", []).append(
            {
                "transaction_type": "refund",
                "amount": refund_amount,
                "payment_method_id": payment_method_id,
            }
        )
        self.record_mutation()

    def apply_modify_pending_order_items(
        self,
        order: dict[str, Any],
        item_ids: list[str],
        new_item_ids: list[str],
        payment_method_id: str,
        price_delta: float,
    ) -> None:
        by_old_id = dict(zip(item_ids, new_item_ids))
        for item in order["items"]:
            if item["item_id"] in by_old_id:
                new_item_id = by_old_id[item["item_id"]]
                _, variant = self.find_item(new_item_id)
                item["item_id"] = new_item_id
                item["price"] = variant["price"]
        order["total"] = round(sum(item["price"] for item in order["items"]), 2)
        order.setdefault("payment_history", []).append(
            {
                "transaction_type": "adjustment",
                "amount": price_delta,
                "payment_method_id": payment_method_id,
            }
        )
        self.record_mutation()

    def apply_modify_pending_order_payment(self, order: dict[str, Any], payment_method_id: str) -> None:
        order.setdefault("payment_history", []).append(
            {
                "transaction_type": "payment_method_change",
                "amount": order["total"],
                "payment_method_id": payment_method_id,
            }
        )
        self.record_mutation()

    def apply_modify_pending_order_address(self, order: dict[str, Any], address: dict[str, str]) -> None:
        order["address"] = dict(address)
        self.record_mutation()

    def apply_modify_user_address(self, user: dict[str, Any], address: dict[str, str]) -> None:
        user["address"] = dict(address)
        self.record_mutation()
