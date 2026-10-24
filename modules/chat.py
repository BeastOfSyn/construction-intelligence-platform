"""Construction engineering assistant: system prompt, demo replies, runner."""
from __future__ import annotations

from typing import Dict, List, Sequence, Tuple

from .ai_client import AIClient, ChatResult

SYSTEM_PROMPT = (
    "You are a construction engineering assistant for Indian building sites. "
    "Give concise, practical answers. Cite relevant standards when useful (IS codes such as "
    "IS 456, IS 800, IS 3764, IS 7969, and OSHA 29 CFR 1926). "
    "You must never certify that a structure or site is safe. For safety-critical questions, "
    "end with a reminder to consult a licensed engineer or the site safety officer."
)

SAFETY_REMINDER = "\n\n_Safety-critical topic: confirm with a licensed engineer or your site safety officer._"

# (keywords, reply) - first match wins; order matters.
_DEMO_RULES: List[Tuple[Tuple[str, ...], str]] = [
    (
        ("curing", "cure"),
        "Keep concrete moist for at least 7 days (10 days with blended cement or in hot weather), "
        "per IS 456. Start wet curing as soon as the surface can take it without damage, use "
        "ponding, wet burlap or curing compound, and avoid direct sun and wind." + SAFETY_REMINDER,
    ),
    (
        ("concrete", "slump", "pour", "mix"),
        "For routine RCC work, M20-M25 is common. Check slump at the point of placement, compact "
        "with vibrators to avoid honeycombing, maintain cover to the bars, and cast cubes for "
        "28-day strength testing (IS 456 / IS 516)." + SAFETY_REMINDER,
    ),
    (
        ("scaffold",),
        "Scaffolds need a firm base, proper bracing and ties, complete guardrails and toe boards, "
        "and an inspection by a competent person before each shift and after bad weather "
        "(see IS 4014 and OSHA 1926 Subpart L)." + SAFETY_REMINDER,
    ),
    (
        ("height", "harness", "fall"),
        "Before work at height: inspect the harness and lanyard, confirm a rated anchor point, "
        "install edge protection, check the permit to work, and make sure nobody works alone "
        "(OSHA 1926 Subpart M, IS 3696)." + SAFETY_REMINDER,
    ),
    (
        ("ppe", "helmet", "vest", "boots"),
        "Minimum site PPE: safety helmet, high-vis vest, safety boots with steel toe, gloves and "
        "eye protection. Add a harness at height, hearing protection near loud machinery, and "
        "respirators for dust or fumes." + SAFETY_REMINDER,
    ),
    (
        ("cement",),
        "A typical estimate is about 0.4 bag of cement per sq ft of built-up area for a "
        "framed building. Store bags off the ground, in a dry shed, stacked no more than 10 high, "
        "and use older stock first.",
    ),
    (
        ("steel", "rebar", "reinforcement"),
        "A thumb rule is about 4 kg of steel per sq ft of built-up area for framed residential "
        "construction. Check bar grade (Fe500/Fe500D), bending schedules, lap lengths and cover "
        "against the structural drawings." + SAFETY_REMINDER,
    ),
    (
        ("rain", "monsoon", "wet"),
        "In heavy rain: isolate temporary electrics, protect fresh concrete from washout, pump out "
        "excavations, check shoring, and postpone pours and external finishing." + SAFETY_REMINDER,
    ),
]
_DEFAULT_REPLY = (
    "I can help with concrete and curing, scaffolding, work at height, PPE, material quantities, "
    "and weather precautions. This is demo mode, so answers are general guidance. "
    "Try asking: 'What should I check before starting work at height?'"
)


def demo_reply(message: str) -> str:
    """Return a keyword-based canned answer for demo mode."""
    text = message.lower()
    for keywords, reply in _DEMO_RULES:
        if any(k in text for k in keywords):
            return reply
    return _DEFAULT_REPLY


def get_reply(client: AIClient, history: Sequence[Dict[str, str]], message: str) -> ChatResult:
    """Answer ``message`` in the context of earlier turns."""
    return client.chat(history, message, SYSTEM_PROMPT, demo_reply)
