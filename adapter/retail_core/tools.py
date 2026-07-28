"""Canonical tool handlers: thin business-rule logic against RetailDB.

Tool names and input shapes here are pinned by tools/tau_retail_contract.json
/ tools/schemas/*.schema.json (WS3 canonical contract v0.2.0, candidate for
owner review) -- do not rename or reshape without a contract-version update.

RetailEnv.call_tool() already rejected disallowed tools and schema-invalid
arguments before a handler ever runs (see env.py), so a handler here only
ever returns one of errors.HANDLER_ERROR_CODES: not_found, invalid_state,
duplicate_action, policy_rejected, tool_failure, timeout, internal_error.

Every mutation handler follows the same shape: look up the referenced
entities (not_found) -> check the idempotency ledger (duplicate_action) ->
check business preconditions (invalid_state / policy_rejected) -> only then
mutate. On any failure the function returns before touching db state. A
repeated identical mutation is a hard `duplicate_action` error, not a silent
no-op: state_changed is False on the repeat and both calls still appear in
the trace, per docs/ws3_tau_retail_contract.md's "State and mutation
evidence" section.
"""

import ast
import operator
from typing import Any

from adapter.retail_core import errors
from adapter.retail_core.db import RetailDB
from adapter.retail_core.schemas import ToolResult

PENDING_ORDER_STATUSES = {"pending"}
DELIVERED_ORDER_STATUSES = {"delivered"}

_CALCULATOR_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.USub: operator.neg,
}


def _not_found(message: str) -> ToolResult:
    return ToolResult(ok=False, error_type=errors.NOT_FOUND, error_message=message)


def _invalid_state(message: str) -> ToolResult:
    return ToolResult(ok=False, error_type=errors.INVALID_STATE, error_message=message)


def _duplicate(message: str) -> ToolResult:
    return ToolResult(ok=False, error_type=errors.DUPLICATE_ACTION, error_message=message)


def _policy_rejected(message: str) -> ToolResult:
    return ToolResult(ok=False, error_type=errors.POLICY_REJECTED, error_message=message)


def _internal_error(message: str) -> ToolResult:
    return ToolResult(ok=False, error_type=errors.INTERNAL_ERROR, error_message=message)


def _injected_failure(db: RetailDB, key: tuple) -> ToolResult | None:
    """Consume a test-injected failure for this exact call, if one is queued."""
    error_type = db.pop_injected_failure(key)
    if error_type is None:
        return None
    return ToolResult(ok=False, error_type=error_type, error_message=f"injected {error_type} for {key}")


# -- read tools -----------------------------------------------------------


def get_user_details(db: RetailDB, arguments: dict[str, Any]) -> ToolResult:
    user_id = arguments["user_id"]
    user = db.get_user(user_id)
    if user is None:
        return _not_found(f"unknown user_id: {user_id}")
    return ToolResult(ok=True, data=user, state_changed=False)


def get_order_details(db: RetailDB, arguments: dict[str, Any]) -> ToolResult:
    order_id = arguments["order_id"]
    order = db.get_order(order_id)
    if order is None:
        return _not_found(f"unknown order_id: {order_id}")
    return ToolResult(ok=True, data=order, state_changed=False)


def get_product_details(db: RetailDB, arguments: dict[str, Any]) -> ToolResult:
    product_id = arguments["product_id"]
    product = db.get_product(product_id)
    if product is None:
        return _not_found(f"unknown product_id: {product_id}")
    return ToolResult(ok=True, data=product, state_changed=False)


def get_item_details(db: RetailDB, arguments: dict[str, Any]) -> ToolResult:
    item_id = arguments["item_id"]
    found = db.find_item(item_id)
    if found is None:
        return _not_found(f"unknown item_id: {item_id}")
    _, variant = found
    return ToolResult(ok=True, data=variant, state_changed=False)


def list_all_product_types(db: RetailDB, arguments: dict[str, Any]) -> ToolResult:
    products = sorted(
        (product["name"], product["product_id"]) for product in db.products.values()
    )
    return ToolResult(ok=True, data=dict(products), state_changed=False)


def find_user_id_by_email(db: RetailDB, arguments: dict[str, Any]) -> ToolResult:
    user_id = db.find_user_id_by_email(arguments["email"])
    if user_id is None:
        return _not_found(f"no user with email: {arguments['email']}")
    return ToolResult(ok=True, data={"user_id": user_id}, state_changed=False)


def find_user_id_by_name_zip(db: RetailDB, arguments: dict[str, Any]) -> ToolResult:
    user_id = db.find_user_id_by_name_zip(
        arguments["first_name"], arguments["last_name"], arguments["zip"]
    )
    if user_id is None:
        return _not_found("no user matches the given first_name/last_name/zip")
    return ToolResult(ok=True, data={"user_id": user_id}, state_changed=False)


def calculate(db: RetailDB, arguments: dict[str, Any]) -> ToolResult:
    """Evaluate a bounded arithmetic expression (+-*/, parens, unary minus).

    The input schema already restricts ``expression`` to digits/operators/
    parens/whitespace, so this never receives arbitrary code -- ast.parse
    plus a fixed operator whitelist keeps eval() out of the picture entirely.
    """
    expression = arguments["expression"]
    try:
        tree = ast.parse(expression, mode="eval")
        value = _eval_arithmetic(tree.body)
    except ZeroDivisionError:
        return _internal_error(f"division by zero in expression: {expression}")
    except Exception as exc:  # malformed expression that still passed the schema pattern
        return _internal_error(f"could not evaluate expression {expression!r}: {exc}")
    return ToolResult(ok=True, data={"result": value}, state_changed=False)


def _eval_arithmetic(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _CALCULATOR_OPS:
        return _CALCULATOR_OPS[type(node.op)](_eval_arithmetic(node.left), _eval_arithmetic(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _CALCULATOR_OPS:
        return _CALCULATOR_OPS[type(node.op)](_eval_arithmetic(node.operand))
    raise ValueError(f"unsupported expression node: {ast.dump(node)}")


def transfer_to_human_agents(db: RetailDB, arguments: dict[str, Any]) -> ToolResult:
    ticket_id = db.next_id("HUMAN-")
    return ToolResult(
        ok=True,
        data={"ticket_id": ticket_id, "summary": arguments["summary"]},
        state_changed=False,
    )


# -- mutation tools ---------------------------------------------------------


def cancel_pending_order(db: RetailDB, arguments: dict[str, Any]) -> ToolResult:
    order_id, reason = arguments["order_id"], arguments["reason"]
    order = db.get_order(order_id)
    if order is None:
        return _not_found(f"unknown order_id: {order_id}")

    ledger_key = ("cancel_pending_order", order_id)
    if db.already_applied(ledger_key):
        return _duplicate(f"order {order_id} was already cancelled")

    failure = _injected_failure(db, ledger_key)
    if failure is not None:
        return failure

    if order["status"] not in PENDING_ORDER_STATUSES:
        return _invalid_state(f"order {order_id} is not pending (status={order['status']})")

    db.apply_cancel_pending_order(order, reason)
    db.mark_applied(ledger_key)
    return ToolResult(ok=True, data={"order_id": order_id, "status": order["status"]}, state_changed=True)


def _resolve_exchange(
    db: RetailDB, order: dict[str, Any], item_ids: list[str], new_item_ids: list[str]
) -> tuple[float, ToolResult | None]:
    if len(item_ids) != len(new_item_ids):
        return 0.0, _policy_rejected("item_ids and new_item_ids must be the same length")
    order_items = {item["item_id"]: item for item in order["items"]}
    price_delta = 0.0
    for old_id, new_id in zip(item_ids, new_item_ids):
        if old_id not in order_items:
            return 0.0, _policy_rejected(f"order does not contain item {old_id}")
        found = db.find_item(new_id)
        if found is None:
            return 0.0, _not_found(f"unknown item_id: {new_id}")
        _, variant = found
        if not variant.get("available", False):
            return 0.0, _policy_rejected(f"item {new_id} is not available")
        price_delta += round(variant["price"] - order_items[old_id]["price"], 2)
    return price_delta, None


def exchange_delivered_order_items(db: RetailDB, arguments: dict[str, Any]) -> ToolResult:
    order_id = arguments["order_id"]
    item_ids, new_item_ids = arguments["item_ids"], arguments["new_item_ids"]
    payment_method_id = arguments["payment_method_id"]
    order = db.get_order(order_id)
    if order is None:
        return _not_found(f"unknown order_id: {order_id}")

    ledger_key = ("exchange_delivered_order_items", order_id, tuple(item_ids), tuple(new_item_ids), payment_method_id)
    if db.already_applied(ledger_key):
        return _duplicate(f"this exchange was already applied for order {order_id}")

    if order["status"] not in DELIVERED_ORDER_STATUSES:
        return _invalid_state(f"order {order_id} is not delivered (status={order['status']})")

    user = db.get_user(order["user_id"])
    if payment_method_id not in (user or {}).get("payment_methods", {}):
        return _not_found(f"unknown payment_method_id: {payment_method_id}")

    price_delta, failure = _resolve_exchange(db, order, item_ids, new_item_ids)
    if failure is not None:
        return failure

    db.apply_exchange_delivered_order_items(order, item_ids, new_item_ids, payment_method_id, price_delta)
    db.mark_applied(ledger_key)
    return ToolResult(
        ok=True,
        data={"order_id": order_id, "status": order["status"], "price_delta": price_delta},
        state_changed=True,
    )


def return_delivered_order_items(db: RetailDB, arguments: dict[str, Any]) -> ToolResult:
    order_id = arguments["order_id"]
    item_ids = arguments["item_ids"]
    payment_method_id = arguments["payment_method_id"]
    order = db.get_order(order_id)
    if order is None:
        return _not_found(f"unknown order_id: {order_id}")

    ledger_key = ("return_delivered_order_items", order_id, tuple(item_ids), payment_method_id)
    if db.already_applied(ledger_key):
        return _duplicate(f"these items were already returned for order {order_id}")

    if order["status"] not in DELIVERED_ORDER_STATUSES:
        return _invalid_state(f"order {order_id} is not delivered (status={order['status']})")

    user = db.get_user(order["user_id"])
    if payment_method_id not in (user or {}).get("payment_methods", {}):
        return _not_found(f"unknown payment_method_id: {payment_method_id}")

    order_items = {item["item_id"]: item for item in order["items"]}
    already_returned = set(order.get("returned_items", []))
    refund_amount = 0.0
    for item_id in item_ids:
        if item_id not in order_items:
            return _policy_rejected(f"order {order_id} does not contain item {item_id}")
        if item_id in already_returned:
            return _policy_rejected(f"item {item_id} was already returned for order {order_id}")
        refund_amount += order_items[item_id]["price"]

    db.apply_return_delivered_order_items(order, item_ids, payment_method_id, round(refund_amount, 2))
    db.mark_applied(ledger_key)
    return ToolResult(
        ok=True,
        data={"order_id": order_id, "status": order["status"], "refund_amount": round(refund_amount, 2)},
        state_changed=True,
    )


def modify_pending_order_items(db: RetailDB, arguments: dict[str, Any]) -> ToolResult:
    order_id = arguments["order_id"]
    item_ids, new_item_ids = arguments["item_ids"], arguments["new_item_ids"]
    payment_method_id = arguments["payment_method_id"]
    order = db.get_order(order_id)
    if order is None:
        return _not_found(f"unknown order_id: {order_id}")

    ledger_key = ("modify_pending_order_items", order_id, tuple(item_ids), tuple(new_item_ids), payment_method_id)
    if db.already_applied(ledger_key):
        return _duplicate(f"this item modification was already applied for order {order_id}")

    if order["status"] not in PENDING_ORDER_STATUSES:
        return _invalid_state(f"order {order_id} is not pending (status={order['status']})")

    user = db.get_user(order["user_id"])
    if payment_method_id not in (user or {}).get("payment_methods", {}):
        return _not_found(f"unknown payment_method_id: {payment_method_id}")

    price_delta, failure = _resolve_exchange(db, order, item_ids, new_item_ids)
    if failure is not None:
        return failure

    db.apply_modify_pending_order_items(order, item_ids, new_item_ids, payment_method_id, price_delta)
    db.mark_applied(ledger_key)
    return ToolResult(
        ok=True,
        data={"order_id": order_id, "total": order["total"], "price_delta": price_delta},
        state_changed=True,
    )


def modify_pending_order_payment(db: RetailDB, arguments: dict[str, Any]) -> ToolResult:
    order_id, payment_method_id = arguments["order_id"], arguments["payment_method_id"]
    order = db.get_order(order_id)
    if order is None:
        return _not_found(f"unknown order_id: {order_id}")

    ledger_key = ("modify_pending_order_payment", order_id, payment_method_id)
    if db.already_applied(ledger_key):
        return _duplicate(f"payment method already set to {payment_method_id} for order {order_id}")

    if order["status"] not in PENDING_ORDER_STATUSES:
        return _invalid_state(f"order {order_id} is not pending (status={order['status']})")

    user = db.get_user(order["user_id"])
    if payment_method_id not in (user or {}).get("payment_methods", {}):
        return _not_found(f"unknown payment_method_id: {payment_method_id}")

    db.apply_modify_pending_order_payment(order, payment_method_id)
    db.mark_applied(ledger_key)
    return ToolResult(ok=True, data={"order_id": order_id, "payment_method_id": payment_method_id}, state_changed=True)


def _address_from_arguments(arguments: dict[str, Any]) -> dict[str, str]:
    return {
        "address1": arguments["address1"],
        "address2": arguments.get("address2", ""),
        "city": arguments["city"],
        "state": arguments["state"],
        "country": arguments["country"],
        "zip": arguments["zip"],
    }


def modify_pending_order_address(db: RetailDB, arguments: dict[str, Any]) -> ToolResult:
    order_id = arguments["order_id"]
    order = db.get_order(order_id)
    if order is None:
        return _not_found(f"unknown order_id: {order_id}")

    address = _address_from_arguments(arguments)
    ledger_key = ("modify_pending_order_address", order_id, tuple(sorted(address.items())))
    if db.already_applied(ledger_key):
        return _duplicate(f"order {order_id} address was already set to this value")

    if order["status"] not in PENDING_ORDER_STATUSES:
        return _invalid_state(f"order {order_id} is not pending (status={order['status']})")

    db.apply_modify_pending_order_address(order, address)
    db.mark_applied(ledger_key)
    return ToolResult(ok=True, data={"order_id": order_id, "address": address}, state_changed=True)


def modify_user_address(db: RetailDB, arguments: dict[str, Any]) -> ToolResult:
    user_id = arguments["user_id"]
    user = db.get_user(user_id)
    if user is None:
        return _not_found(f"unknown user_id: {user_id}")

    address = _address_from_arguments(arguments)
    ledger_key = ("modify_user_address", user_id, tuple(sorted(address.items())))
    if db.already_applied(ledger_key):
        return _duplicate(f"user {user_id} address was already set to this value")

    db.apply_modify_user_address(user, address)
    db.mark_applied(ledger_key)
    return ToolResult(ok=True, data={"user_id": user_id, "address": address}, state_changed=True)


TOOL_HANDLERS = {
    "calculate": calculate,
    "cancel_pending_order": cancel_pending_order,
    "exchange_delivered_order_items": exchange_delivered_order_items,
    "find_user_id_by_email": find_user_id_by_email,
    "find_user_id_by_name_zip": find_user_id_by_name_zip,
    "get_item_details": get_item_details,
    "get_order_details": get_order_details,
    "get_product_details": get_product_details,
    "get_user_details": get_user_details,
    "list_all_product_types": list_all_product_types,
    "modify_pending_order_address": modify_pending_order_address,
    "modify_pending_order_items": modify_pending_order_items,
    "modify_pending_order_payment": modify_pending_order_payment,
    "modify_user_address": modify_user_address,
    "return_delivered_order_items": return_delivered_order_items,
    "transfer_to_human_agents": transfer_to_human_agents,
}
