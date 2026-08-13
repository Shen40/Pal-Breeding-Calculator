from typing import Dict, List, Optional, Set, Tuple, Union

ComboEntry = Union[str, Dict[str, str]]


def normalize_unique_combos(unique_combos: Dict) -> Dict[Tuple[str, str], ComboEntry]:
    """Rekeys unique_combos.json's "Name1,Name2" string keys into sorted-name tuples.

    A combo entry is either a plain child name, or (for the rare pair whose result
    depends on which parent is male, e.g. Katress/Wixen) a dict mapping the male
    parent's species name to the resulting child.
    """
    return {
        tuple(sorted(name.strip() for name in combo_key.split(","))): child
        for combo_key, child in unique_combos.items()
    }


def resolve_combo_children(entry: ComboEntry) -> Set[str]:
    """All possible child species a combo entry can produce, regardless of gender."""
    if isinstance(entry, dict):
        return set(entry.values())
    return {entry}


def compute_excluded_children(normalized_combos: Dict[Tuple[str, str], ComboEntry]) -> Set[str]:
    """Pals only obtainable through a special combo, and therefore not part of the
    general "closest combined power" candidate pool."""
    excluded: Set[str] = set()
    for entry in normalized_combos.values():
        excluded |= resolve_combo_children(entry)
    return excluded


def calculate_child(
    parent_a_name: str,
    parent_b_name: str,
    pals: List[Dict],
    unique_combos: Dict,
    male_name: Optional[str] = None,
    pal_map: Optional[Dict[str, Dict]] = None,
    normalized_combos: Optional[Dict[Tuple[str, str], ComboEntry]] = None,
    excluded_children: Optional[Set[str]] = None,
) -> str:
    """Determines the child species produced by two parent Pals.

    pal_map / normalized_combos / excluded_children may be precomputed once and
    passed in by callers that evaluate many pairs (e.g. the reverse lookup table
    builder), to avoid redoing that O(pals + combos) work on every single call.
    """
    if pal_map is None:
        pal_map = {p["name"]: p for p in pals}

    if parent_a_name not in pal_map or parent_b_name not in pal_map:
        raise ValueError("Invalid Pal name provided.")

    p1 = pal_map[parent_a_name]
    p2 = pal_map[parent_b_name]

    if normalized_combos is None:
        normalized_combos = normalize_unique_combos(unique_combos)

    pair_key = tuple(sorted([p1["name"], p2["name"]]))
    if pair_key in normalized_combos:
        entry = normalized_combos[pair_key]
        if isinstance(entry, dict):
            if male_name in entry:
                return entry[male_name]
            # Gender unknown/unspecified: fall back to a deterministic default.
            return entry[min(entry)]
        return entry

    if p1["name"] == p2["name"]:
        return p1["name"]

    if excluded_children is None:
        excluded_children = compute_excluded_children(normalized_combos)

    target_power = (p1["power"] + p2["power"] + 1) // 2

    best_pal = None
    min_diff = float("inf")

    for candidate in pals:
        if candidate["name"] in excluded_children:
            continue
        diff = abs(candidate["power"] - target_power)
        if diff < min_diff:
            min_diff = diff
            best_pal = candidate
        elif diff == min_diff:
            if candidate["index"] < best_pal["index"]:
                best_pal = candidate

    return best_pal["name"]
