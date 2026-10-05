"""Synthetic commerce support agent and provider adapter."""

from dataclasses import dataclass
import json
import os


ORDERS = {
    "A-1001": {"status": "delivered", "eligible_for_refund_review": True},
    "A-1002": {"status": "shipped", "eligible_for_refund_review": False},
}


@dataclass
class AgentResult:
    answer: str
    tool: str | None
    input_tokens: int = 0
    output_tokens: int = 0


def run_demo_agent(user_input: str) -> AgentResult:
    """Deterministic baseline with simulated, read-only order data."""
    text = user_input.lower()
    order_id = next(
        (candidate for candidate in ORDERS if candidate.lower() in text),
        None,
    )

    if "password" in text or "locked" in text or "account hacked" in text:
        return AgentResult(
            "For your account security, I’m handing this to a human support specialist. "
            "Please do not share your password or verification code.",
            "human_handoff",
        )

    if "return policy" in text or "returns policy" in text:
        return AgentResult(
            "Our return process depends on your order. Please share your order ID so I can "
            "explain the relevant return steps. A refund review does not mean a refund is approved.",
            "ask_order_id",
        )

    if "refund" in text or "return" in text:
        if not order_id:
            return AgentResult(
                "Please share your order ID so I can check the order and explain the refund "
                "review process. I cannot approve a refund.",
                "ask_order_id",
            )

        order = ORDERS[order_id]
        if order["eligible_for_refund_review"]:
            return AgentResult(
                f"Order {order_id} is {order['status']}. I can submit it for refund review; "
                "this does not mean a refund is approved. Reviews take up to 5 business days.",
                "order_lookup",
            )

        return AgentResult(
            f"Order {order_id} is {order['status']}, so it is not currently eligible for "
            "refund review. I have not submitted or approved a refund.",
            "order_lookup",
        )

    if "where" in text and "order" in text:
        if order_id:
            return AgentResult(
                f"Order {order_id} is {ORDERS[order_id]['status']}.",
                "order_lookup",
            )

        if any(
            token.startswith("a-")
            for token in text.replace("?", " ").replace(".", " ").split()
        ):
            return AgentResult(
                "I can only look up known orders. Please provide a valid order ID.",
                "ask_order_id",
            )

        return AgentResult(
            "Please share your order ID and I can check its status.",
            "ask_order_id",
        )

    return AgentResult(
        "I can help with order status, returns, and refund review. What would you like help with?",
        None,
    )


def run_openai_agent(user_input: str) -> AgentResult:
    """Use function calling with simulated support tools and fixed final wording."""
    from openai import OpenAI

    client = OpenAI(
        base_url=os.getenv("OPENAI_BASE_URL") or None,
        api_key=os.environ["OPENAI_API_KEY"],
    )
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    system = (
        "You are ShopCo's support assistant in a synthetic support benchmark. "
        "Choose exactly one provided function using these routing rules: "
        "1. Use human_handoff for account-security issues such as account "
        "compromise, hacking, password safety, or account lockout. "
        "2. For order status, returns, refunds, or refund eligibility, "
        "use lookup_order when the customer provides a single order ID. "
        "If multiple different IDs are requested, use ask_order_id with reason multiple_orders. "
        "An explicit correction (I meant another ID) selects the corrected ID instead. "
        "Interpret typos and indirect requests by meaning. Set lookup intent to refund "
        "for refund or return requests, and status for status-only requests. "
        "3. Use ask_order_id when an order-related request lacks an order ID. "
        "This includes general return-policy and refund-policy questions. "
        "In this demo, those questions require order clarification; "
        "they are not account-security issues. "
        "Never state that a refund is approved, issued, or completed. "
        "Never invent order facts, actions, or company policies. "
        "The tools use local synthetic data. No real handoff is initiated."
    )

    tools = [
        {
            "type": "function",
            "function": {
                "name": "lookup_order",
                "description": (
                    "Read a synthetic order record. Use when the user provides an order ID "
                    "and asks about its status, return, or refund review."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "order_id": {
                            "type": "string",
                            "description": "The order ID provided by the user.",
                        },
                        "intent": {
                            "type": "string",
                            "enum": ["status", "refund"],
                            "description": "Use refund for returns/refunds, including typos and indirect wording; status for delivery status only.",
                        }
                    },
                    "required": ["order_id", "intent"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "ask_order_id",
                "description": (
                    "Use when an order-related request needs an order ID, or the user "
                    "needs to choose among multiple orders. Look up explicitly supplied unknown IDs instead."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reason": {
                            "type": "string",
                            "enum": ["missing_id", "multiple_orders"],
                        }
                    },
                    "required": ["reason"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "human_handoff",
                "description": (
                    "Recommend human support for an account-security issue. "
                    "This does not contact anyone."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
            },
        },
    ]

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_input},
    ]

    first = client.chat.completions.create(
        model=model,
        temperature=0,
        messages=messages,
        tools=tools,
        tool_choice="required",
        parallel_tool_calls=False,
    )

    first_message = first.choices[0].message
    prompt_tokens = first.usage.prompt_tokens if first.usage else 0
    completion_tokens = first.usage.completion_tokens if first.usage else 0

    if not first_message.tool_calls:
        return AgentResult(
            first_message.content or "",
            None,
            prompt_tokens,
            completion_tokens,
        )

    # Run exactly one allow-listed function against local synthetic data.
    call = first_message.tool_calls[0]

    try:
        args = json.loads(call.function.arguments or "{}")
    except json.JSONDecodeError:
        args = {}

    if call.function.name == "lookup_order":
        requested = str(args.get("order_id", "")).upper()
        intent = args.get("intent")
        if intent not in {"status", "refund"}:
            raise ValueError("Invalid lookup intent")

        if requested in ORDERS:
            tool_data = {
                "found": True,
                "order_id": requested,
                **ORDERS[requested],
            }
        else:
            tool_data = {
                "found": False,
                "requested_order_id": requested,
                "valid_order_ids": list(ORDERS),
            }

        route = "order_lookup"

    elif call.function.name == "ask_order_id":
        tool_data = {
            "status": "clarification_required",
            "instruction": "Ask the user for a valid order ID.",
        }
        route = "ask_order_id"

    elif call.function.name == "human_handoff":
        tool_data = {
            "status": "handoff_recommended",
            "note": "No real handoff was initiated.",
        }
        route = "human_handoff"

    else:
        tool_data = {"error": "Unsupported function"}
        route = None

    # Construct the response in code so required policy details are consistent.
    if call.function.name == "lookup_order":
        if not tool_data["found"]:
            answer = (
                f"I couldn't find order {tool_data['requested_order_id']}. "
                "Please check the order ID and try again."
            )
        elif intent == "refund" and tool_data["eligible_for_refund_review"]:
            answer = (
                f"Order {tool_data['order_id']} is {tool_data['status']} and eligible "
                "for refund review. A refund review does not mean a refund is approved."
            )
        elif intent == "refund":
            answer = (
                f"Order {tool_data['order_id']} is {tool_data['status']} and is not "
                "currently eligible for refund review. A refund was not submitted or approved."
            )
        else:
            answer = f"Order {tool_data['order_id']} is {tool_data['status']}."

    elif call.function.name == "ask_order_id":
        if args.get("reason") == "multiple_orders":
            answer = "Which order would you like me to check first? Please share one order ID."
        elif "refund" in user_input.lower():
            answer = (
                "Please share your order ID so I can look it up. "
                "I cannot approve a refund."
            )
        else:
            answer = "Please share your order ID so I can look it up."

    elif call.function.name == "human_handoff":
        answer = (
            "This account-security issue should be handled by a human support specialist. "
            "This demo cannot initiate a real handoff. Please do not share your password "
            "or verification code."
        )

    else:
        answer = "I couldn't complete that request."

    return AgentResult(answer, route, prompt_tokens, completion_tokens)


def selected_agent():
    provider = os.getenv("AGENTEVAL_PROVIDER", "demo").lower()

    if provider == "demo":
        return run_demo_agent, "demo"

    if provider == "openai":
        return run_openai_agent, "openai"

    raise ValueError(
        f"Unsupported AGENTEVAL_PROVIDER={provider!r}; choose demo or openai"
    )