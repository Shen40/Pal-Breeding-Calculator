import json
from src.engine.breeding_calculator import calculate_child

def test_penking_bushi_yields_sibelyx():
    with open("data/pals.json") as f:
        pals = json.load(f)
    with open("data/unique_combos.json") as f:
        combos = json.load(f)

    # Penking (breeding power 2070, from paldb.cc) + Bushi (1560) -> target 1815.
    # Xenovader (1820) and Sibelyx (1810) tie at diff 5; Sibelyx wins the index tiebreak.
    child = calculate_child("Penking", "Bushi", pals, combos)
    assert child == "Sibelyx"