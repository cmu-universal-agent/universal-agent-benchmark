"""Canonical tool handlers: thin business-rule logic against RetailDB.

Tool names here (get_user, get_order, get_product, refund_order,
exchange_item, return_item, escalate_to_human) are placeholders pending
Jessica's canonical contract v1 -- swap the names in TOOL_HANDLERS below
when it lands, the handler bodies shouldn't need to change.

Every mutation handler follows the same shape: validate args -> check
business preconditions -> check the idempotency ledger -> only then mutate.
On any failure the function returns before touching db state.

Duplicate semantics (pinned per WS3 build guide section 6, pending
Chloe/Lanfang sign-off): a repeated identical mutation is a hard
`duplicate_mutation` error, not a silent no-op. state_changed is False on
the repeat and both calls still appear in the trace.
"""

from typing import Any

from adapter.retail_core import errors
from adapter.retail_core.db import RetailDB
from adapter.retail_core.schemas import ToolResult

REFUNDABLE_ORDER_STATUSES = {"delivered"}
RETURNABLE_ORDER_STATUSES = {"delivered"}


def _require_fields(arguments: dict[str, Any], fields: list[str]) -> str | None:
    if not isinstance(arguments, dict):
        return "arguments must be an object"
    missing = [f for f in fields if f not in arguments or arguments[f] in (None, "")]
    if missing:
        return f"missing required argument(s): {', '.join(missing)}"
    return None


def _invalid(message: str) -> ToolResult:
    return ToolResult(ok=False, error_code=errors.INVALID_ARGUMENTS, error_message=message)


def _disallowed(message: str) -> ToolResult:
    return ToolResult(ok=False, error_code=errors.DISALLOWED_ACTION, error_message=message)


def _duplicate(message: str) -> ToolResult:
    return ToolResult(ok=False, error_code=errors.DUPLICATE_MUTATION, error_message=message)


# -- read tools -----------------------------------------------------------


def get_user(db: RetailDB, arguments: dict[str, Any]) -> ToolResult:
    err = _require_fields(arguments, ["user_id"])
    if err:
        return _invalid(err)
    user = db.get_user(arguments["user_id"])
    if user is None:
        return _disallowed(f"unknown user_id: {arguments['user_id']}")
    return ToolResult(ok=True, data=user, state_changed=False)


def get_order(db: RetailDB, arguments: dict[str, Any]) -> ToolResult:
    err = _require_fields(arguments, ["order_id"])
    if err:
        return _invalid(err)
    order = db.get_order(arguments["order_id"])
    if order is None:
        return _disallowed(f"unknown order_id: {arguments['order_id']}")
    return ToolResult(ok=True, data=order, state_changed=False)


def get_product(db: RetailDB, arguments: dict[str, Any]) -> ToolResult:
    err = _require_fields(arguments, ["product_id"])
    if err:
        return _invalid(err)
    product = db.get_product(arguments["product_id"])
    if product is None:
        return _disallowed(f"unknown product_id: {arguments['product_id']}")
    return ToolResult(ok=True, data=product, state_changed=False)


# -- mutation tools ---------------------------------------------------------


def refund_order(db: RetailDB, arguments: dict[str, Any]) -> ToolResult:
    err = _require_fields(arguments, ["order_id", "reason"])
    if err:
        return _invalid(err)

    order_id = arguments["order_id"]
    order = db.get_order(order_id)
    if order is None:
        return _disallowed(f"unknown order_id: {order_id}")

    # Duplicate check runs before the precondition check: a successful
    # refund moves status out of REFUNDABLE_ORDER_STATUSES, so a repeat of
    # the *same* mutation must be recognized as duplicate_mutation rather
    # than falling through to disallowed_action.
    ledger_key = ("refund_order", order_id)
    if db.already_applied(ledger_key):
        return _duplicate(f"refund already applied for order {order_id}")

    if order["status"] not in REFUNDABLE_ORDER_STATUSES:
        return _disallowed(f"order {order_id} is not in a refundable state (status={order['status']})")

    amount = round(order["total"] - order["refunded_amount"], 2)
    db.apply_refund(order, amount)
    db.mark_applied(ledger_key)
    return ToolResult(
        ok=True,
        data={"order_id": order_id, "status": order["status"], "refunded_amount": order["refunded_amount"]},
        state_changed=True,
    )


def exchange_item(db: RetailDB, arguments: dict[str, Any]) -> ToolResult:
    err = _require_fields(arguments, ["order_id", "old_item_id", "new_item_id"])
    if err:
        return _invalid(err)

    order_id, old_item_id, new_item_id = arguments["order_id"], arguments["old_item_id"], arguments["new_item_id"]
    order = db.get_order(order_id)
    if order is None:
        return _disallowed(f"unknown order_id: {order_id}")

    # Duplicate check first: a successful exchange replaces old_item_id with
    # new_item_id in order["items"] and moves status out of
    # REFUNDABLE_ORDER_STATUSES, so a repeat of the same exchange must not
    # fall through to disallowed_action below.
    ledger_key = ("exchange_item", order_id, old_item_id, new_item_id)
    if db.already_applied(ledger_key):
        return _duplicate(f"exchange {old_item_id} -> {new_item_id} already applied for order {order_id}")

    if order["status"] not in REFUNDABLE_ORDER_STATUSES:
        return _disallowed(f"order {order_id} is not eligible for exchange (status={order['status']})")

    existing_item = next((i for i in order["items"] if i["item_id"] == old_item_id), None)
    if existing_item is None:
        return _disallowed(f"order {order_id} does not contain item {old_item_id}")

    new_variant = None
    for product in db.products.values():
        for variant in product["variants"]:
            if variant["item_id"] == new_item_id:
                new_variant = variant
                break
    if new_variant is None or not new_variant.get("available", False):
        return _disallowed(f"item {new_item_id} is not available for exchange")

    db.apply_exchange(order, old_item_id, new_item_id, new_variant["price"])
    db.mark_applied(ledger_key)
    return ToolResult(
        ok=True,
        data={"order_id": order_id, "status": order["status"], "item_id": new_item_id},
        state_changed=True,
    )


def return_item(db: RetailDB, arguments: dict[str, Any]) -> ToolResult:
    err = _require_fields(arguments, ["order_id", "item_id"])
    if err:
        return _invalid(err)

    order_id, item_id = arguments["order_id"], arguments["item_id"]
    order = db.get_order(order_id)
    if order is None:
        return _disallowed(f"unknown order_id: {order_id}")

    # Duplicate check first: a successful return moves status out of
    # RETURNABLE_ORDER_STATUSES, so a repeat of the same return must not
    # fall through to disallowed_action below.
    ledger_key = ("return_item", order_id, item_id)
    if db.already_applied(ledger_key):
        return _duplicate(f"item {item_id} already returned for order {order_id}")

    if order["status"] not in RETURNABLE_ORDER_STATUSES:
        return _disallowed(f"order {order_id} is not eligible for return (status={order['status']})")
    if not any(i["item_id"] == item_id for i in order["items"]):
        return _disallowed(f"order {order_id} does not contain item {item_id}")

    db.apply_return(order, item_id)
    db.mark_applied(ledger_key)
    return ToolResult(
        ok=True,
        data={"order_id": order_id, "status": order["status"], "item_id": item_id},
        state_changed=True,
    )


def escalate_to_human(db: RetailDB, arguments: dict[str, Any]) -> ToolResult:
    err = _require_fields(arguments, ["order_id", "reason"])
    if err:
        return _invalid(err)

    order_id, reason = arguments["order_id"], arguments["reason"]
    order = db.get_order(order_id)
    if order is None:
        return _disallowed(f"unknown order_id: {order_id}")

    ledger_key = ("escalate_to_human", order_id, reason)
    if db.already_applied(ledger_key):
        return _duplicate(f"order {order_id} already escalated for reason: {reason}")

    ticket_id = db.apply_escalation(order, reason)
    db.mark_applied(ledger_key)
    return ToolResult(ok=True, data={"order_id": order_id, "ticket_id": ticket_id}, state_changed=True)


TOOL_HANDLERS = {
    "get_user": get_user,
    "get_order": get_order,
    "get_product": get_product,
    "refund_order": refund_order,
    "exchange_item": exchange_item,
    "return_item": return_item,
    "escalate_to_human": escalate_to_human,
}
