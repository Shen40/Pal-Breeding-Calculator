from typing import Dict, List, Set, Tuple
from collections import defaultdict
from itertools import combinations_with_replacement
from src.engine.breeding_calculator import (
    calculate_child,
    compute_excluded_children,
    normalize_unique_combos,
    resolve_combo_children,
)

def build_reverse_lookup_table(pals: List[Dict], unqiue_combos: Dict) -> Dict[str, Set[Tuple[str, str]]]:
    reverse_table = defaultdict(set)
    names = [p["name"] for p in pals]
    pal_map = {p["name"]: p for p in pals}
    normalized_combos = normalize_unique_combos(unqiue_combos)
    excluded_children = compute_excluded_children(normalized_combos)

    for p1, p2 in combinations_with_replacement(names, 2):
        pair = tuple(sorted([p1, p2]))

        if pair in normalized_combos:
            for child in resolve_combo_children(normalized_combos[pair]):
                reverse_table[child].add(pair)
            continue

        child = calculate_child(
            p1, p2, pals, unqiue_combos,
            pal_map=pal_map, normalized_combos=normalized_combos, excluded_children=excluded_children
        )
        reverse_table[child].add(pair)
    return dict(reverse_table)