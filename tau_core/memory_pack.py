from __future__ import annotations

from pathlib import Path

from .memory import cards, scoped_cards


def pack_memory(root: Path, scope: str = ".", limit: int = 8) -> dict:
    """Compound tool: pack relevant scoped memory cards into compact format."""
    exact = scoped_cards(root, scope, limit=limit)
    global_c = scoped_cards(root, ".", limit=limit)
    all_cards = list(dict.fromkeys([c["id"] for c in exact + global_c]))
    unique = [c for c in exact if c["id"] not in {x["id"] for x in global_c}]
    unique.extend(global_c)
    cards_list = unique[:limit]
    packed_lines = []
    for c in cards_list:
        line = f"[{c.get('scope', '.')}/{c.get('type','workflow')}] {c['summary']}"
        packed_lines.append(line)
    return {
        "scope": scope,
        "card_count": len(cards_list),
        "cards": cards_list,
        "packed_text": "\n".join(packed_lines),
    }
