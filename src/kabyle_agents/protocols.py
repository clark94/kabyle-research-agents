"""Agent self-description.

Cards are A2A-*shaped* (name, description, skills) so the agents can later be exposed as real
A2A servers; they are not wire-compatible yet. ``identity`` slots are reserved for a DID and an
ERC-8004 registry id, both intentionally empty until that layer is built.
"""

from __future__ import annotations

from .agents import _Agent


def agent_cards(agents: list[_Agent]) -> list[dict]:
    return [
        {
            "name": a.name,
            "description": a.description,
            "skills": [{"id": a.name, "description": a.description}],
            "identity": {"did": None, "erc8004_agent_id": None},
            "status": "draft: A2A-shaped, not wire-compatible",
        }
        for a in agents
    ]
