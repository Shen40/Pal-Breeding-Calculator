import math
from typing import List, Dict, Set, Tuple, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session 

from src.models.pal import UserPal, Gender
from src.schemas import UserPalCreate, UserPalResponse
from src.models.user import User
from src.engine.breeding_calculator import (
    calculate_child,
    normalize_unique_combos,
    resolve_combo_children,
    compute_excluded_children,
)
from src.engine.passive_inheritance_engine import PassiveInheritanceEngine
from src.core.exceptions import (
    PalSpeciesNotFoundError,
    PalInventoryNotFoundError,
    UserNotFoundError,
    NoBreedingCombinationsError,
    PassiveSkillNotFoundError,
)

# How many additional breeding generations beyond the pals directly in the box
# to explore when discovering possible children (breadth-first over species).
MAX_DISCOVERY_GENERATIONS = 4


class BreedingService:
    def __init__(
        self,
        pals_data: List[Dict],
        unique_combos: Dict[str, str],
        reverse_lookup: Dict[str, Set[Tuple[str, str]]],
        passives_data: Optional[List[Dict]] = None
    ):
        self.pals_data = pals_data
        self.unique_combos = unique_combos
        self.reverse_lookup = reverse_lookup
        self.passives_data = passives_data or []

        if isinstance(pals_data, list):
            self.valid_pal_names = {p["name"] for p in pals_data if "name" in p}
        elif isinstance(pals_data, dict):
            self.valid_pal_names = set(pals_data.keys())
        else:
            self.valid_pal_names = set()

        self.valid_passive_names = {p["name"] for p in self.passives_data if "name" in p}

    def get_all_species(self) -> List[str]:
        """Provides a sorted list of all valid species names for the frontend dropdown."""
        return sorted(list(self.valid_pal_names))

    def get_all_passives(self) -> List[Dict]:
        """Provides all known passive skills (name/rank/polarity/description) for the frontend dropdown."""
        return sorted(self.passives_data, key=lambda p: p["name"])

    def add_pal(self, db: Session, user_id: int, pal_in: UserPalCreate) -> UserPal:
        if not db.query(User).filter(User.id == user_id).first():
            raise UserNotFoundError(user_id)
        if pal_in.species_name not in self.valid_pal_names:
            raise PalSpeciesNotFoundError(pal_in.species_name)
        if self.valid_passive_names:
            for passive in pal_in.passives:
                if passive not in self.valid_passive_names:
                    raise PassiveSkillNotFoundError(passive)

        db_pal = UserPal(
            user_id=user_id,
            species_name=pal_in.species_name,
            gender=pal_in.gender,
            passives=pal_in.passives, 
            nickname=pal_in.nickname
        )

        db.add(db_pal)
        db.commit()
        db.refresh(db_pal)
        return db_pal

    def get_inventory(self, db: Session, user_id: int) -> List[UserPal]:
        return db.query(UserPal).filter(UserPal.user_id == user_id).all()

    def delete_pal(self, db: Session, user_id: int, pal_id: int) -> bool:
        pal = db.query(UserPal).filter(UserPal.id == pal_id, UserPal.user_id == user_id).first()
        if not pal:
            raise PalInventoryNotFoundError(pal_id)
        db.delete(pal)
        db.commit()
        return True

    def discover_breedable_pals(self, db: Session, user_id: int) -> Dict[str, List[Dict]]:
        males = db.query(UserPal).filter(UserPal.user_id == user_id, UserPal.gender == Gender.MALE).all()
        females = db.query(UserPal).filter(UserPal.user_id == user_id, UserPal.gender == Gender.FEMALE).all()

        discoveries = {}
        for m in males:
            for f in females:
                child = calculate_child(
                    m.species_name, f.species_name, self.pals_data, self.unique_combos,
                    male_name=m.species_name
                )
                discoveries.setdefault(child, []).append({
                    "male_parent": UserPalResponse.model_validate(m),
                    "female_parent": UserPalResponse.model_validate(f),
                    "generation": 1
                })

        inventory_species = {p.species_name for p in males} | {p.species_name for p in females}
        self._merge_deeper_generations(discoveries, inventory_species)
        return discoveries

    def _merge_deeper_generations(self, discoveries: Dict[str, List[Dict]], inventory_species: Set[str]) -> None:
        """Extends a generation-1 discovery dict with species reachable through further
        breeding generations (breadth-first over species, not real Pal instances)."""
        gen1_children = set(discoveries.keys())
        all_known = inventory_species | gen1_children
        deeper = self._bfs_expand_species(all_known, gen1_children, start_generation=2)
        for child, entries in deeper.items():
            discoveries.setdefault(child, []).extend(entries)

    def _bfs_expand_species(
        self, all_known: Set[str], frontier: Set[str], start_generation: int
    ) -> Dict[str, List[Dict]]:
        """Breadth-first search over species-level breeding reachability.

        Explores which further species become reachable by breeding a newly
        discovered species against anything already known (including other newly
        discovered species), generation by generation, up to MAX_DISCOVERY_GENERATIONS.
        Parents here are species placeholders (no real owned Pal instance yet).
        """
        pal_map = {p["name"]: p for p in self.pals_data}
        normalized_combos = normalize_unique_combos(self.unique_combos)
        excluded_children = compute_excluded_children(normalized_combos)

        all_known = set(all_known)
        frontier = set(frontier)
        processed_pairs: Set[Tuple[str, str]] = set()
        discoveries: Dict[str, List[Dict]] = {}

        generation = start_generation
        while frontier and generation < start_generation + MAX_DISCOVERY_GENERATIONS:
            next_frontier = set()
            for s1 in frontier:
                if s1 not in pal_map:
                    continue
                for s2 in all_known:
                    if s2 not in pal_map:
                        continue
                    pair_key = tuple(sorted([s1, s2]))
                    if pair_key in processed_pairs:
                        continue
                    processed_pairs.add(pair_key)

                    if pair_key in normalized_combos:
                        children = resolve_combo_children(normalized_combos[pair_key])
                    else:
                        children = {calculate_child(
                            s1, s2, self.pals_data, self.unique_combos,
                            pal_map=pal_map, normalized_combos=normalized_combos,
                            excluded_children=excluded_children
                        )}

                    for child in children:
                        if child in all_known:
                            continue
                        discoveries.setdefault(child, []).append({
                            "male_parent": self._virtual_parent(s1),
                            "female_parent": self._virtual_parent(s2),
                            "generation": generation
                        })
                        next_frontier.add(child)

            all_known |= next_frontier
            frontier = next_frontier
            generation += 1

        return discoveries

    @staticmethod
    def _virtual_parent(species_name: str) -> Dict[str, Any]:
        """A placeholder parent for a species not yet in the user's box, used for
        generation-2+ discoveries that require breeding an intermediate Pal first."""
        return {
            "id": 0,
            "user_id": 0,
            "species_name": species_name,
            "gender": None,
            "passives": [],
            "nickname": None,
            "is_intermediate": True
        }

    def discover_breedable_pals_transient(self, inventory: List) -> Dict[str, List[Dict]]:
        """Calculates all possible child species that can be bred from a guest inventory."""
        if not inventory:
            return {}

        def get_attr(item, key):
            if isinstance(item, dict):
                val = item.get(key)
            else:
                val = getattr(item, key, None)
            if hasattr(val, "value"):
                return val.value
            return val

        def clean_str(val):
            return str(val or "").strip().upper()

        males = [p for p in inventory if clean_str(get_attr(p, 'gender')) in ['MALE', 'M']]
        females = [p for p in inventory if clean_str(get_attr(p, 'gender')) in ['FEMALE', 'F']]

        discoveries = {}
        inventory_species = set()
        for m in males:
            m_species = get_attr(m, 'species_name') or get_attr(m, 'species')
            inventory_species.add(str(m_species))
            for f in females:
                f_species = get_attr(f, 'species_name') or get_attr(f, 'species')
                inventory_species.add(str(f_species))

                child = calculate_child(
                    str(m_species), str(f_species), self.pals_data, self.unique_combos,
                    male_name=str(m_species)
                )
                if child:
                    discoveries.setdefault(child, []).append({
                        "male_parent": self._normalize_parent(m),
                        "female_parent": self._normalize_parent(f),
                        "generation": 1
                    })

        self._merge_deeper_generations(discoveries, inventory_species)
        return discoveries

    def _normalize_parent(self, parent: Any) -> Dict[str, Any]:
        """Ensures parent objects carry `id` and `user_id` required by the response schema."""
        if hasattr(parent, "model_dump"):
            data = parent.model_dump()
        elif isinstance(parent, dict):
            data = parent.copy()
        else:
            data = {
                "species_name": getattr(parent, "species_name", getattr(parent, "species", "")),
                "gender": getattr(parent, "gender", ""),
                "passives": getattr(parent, "passives", []),
                "nickname": getattr(parent, "nickname", None)
            }

        # Inject default IDs for transient/guest inventory items
        data.setdefault("id", 0)
        data.setdefault("user_id", 0)

        # Ensure Enum conversion for gender string
        if hasattr(data.get("gender"), "value"):
            data["gender"] = data["gender"].value

        return data

    def _calculate_stats_safely(
        self, male_passives: List[str], female_passives: List[str], desired_passives: List[str], require_clean: bool
    ) -> Dict[str, Any]:
        """Calculates breeding stats and satisfies all schema fields (percentage, expected_eggs, p95_eggs)."""
        male_p = male_passives or []
        female_p = female_passives or []
        unique_passives_count = len(set(male_p) | set(female_p))

        def calc_p95(prob: float) -> int:
            if prob >= 1.0:
                return 1
            if prob <= 0:
                return 0
            return math.ceil(math.log(0.05) / math.log(1.0 - prob))

        # Case 1: No specific passives requested -> 100% success rate
        if not desired_passives:
            return {
                "success_rate": 1.0,
                "percentage": "100.0%",
                "expected_attempts": 1,
                "expected_eggs": 1,
                "p95_eggs": 1,
                "unique_parent_passives": unique_passives_count
            }

        # Case 2: Cap passives list to maximum 4 (Palworld engine limit)
        target_passives = desired_passives[:4]

        try:
            stats = PassiveInheritanceEngine.calculate_exact_target_prob(
                male_p, female_p, target_passives, require_clean
            )
            rate = stats.get("success_rate", stats.get("probability", 0.0))
            expected_eggs = stats.get("expected_eggs", stats.get("expected_attempts", math.ceil(1.0 / rate) if rate > 0 else 0))
            p95 = stats.get("p95_eggs", calc_p95(rate))
            percentage = stats.get("percentage", f"{round(rate * 100.0, 2)}%")

            return {
                "success_rate": rate,
                "percentage": percentage,
                "expected_attempts": expected_eggs,
                "expected_eggs": expected_eggs,
                "p95_eggs": p95,
                "unique_parent_passives": unique_passives_count
            }
        except Exception:
            return {
                "success_rate": 0.0,
                "percentage": "0.0%",
                "expected_attempts": 0,
                "expected_eggs": 0,
                "p95_eggs": 0,
                "unique_parent_passives": unique_passives_count
            }

    def find_pairs_for_target(
        self, db: Session, user_id: int, target_species: str, desired_passives: List[str], require_clean: bool
    ) -> List[Dict]:
        """Calculates breeding probabilities for authenticated users using database inventory."""
        valid_pairs = self.reverse_lookup.get(target_species, set())
        if not valid_pairs:
            raise NoBreedingCombinationsError(target_species)

        needed_species = {species for pair in valid_pairs for species in pair}

        males = db.query(UserPal).filter(
            UserPal.user_id == user_id,
            UserPal.gender == Gender.MALE,
            UserPal.species_name.in_(needed_species)
        ).all()

        females = db.query(UserPal).filter(
            UserPal.user_id == user_id,
            UserPal.gender == Gender.FEMALE,
            UserPal.species_name.in_(needed_species)
        ).all()

        recommendations = []
        for m in males:
            for f in females:
                pair_key = tuple(sorted([m.species_name, f.species_name]))
                if pair_key not in valid_pairs:
                    continue
                actual_child = calculate_child(
                    m.species_name, f.species_name, self.pals_data, self.unique_combos,
                    male_name=m.species_name
                )
                if actual_child == target_species:
                    stats = self._calculate_stats_safely(
                        m.passives, f.passives, desired_passives, require_clean
                    )
                    rate = stats.get("success_rate", 0)
                    if rate > 0:
                        recommendations.append({
                            "male_parent": UserPalResponse.model_validate(m),
                            "female_parent": UserPalResponse.model_validate(f),
                            "child_species": target_species,
                            **stats 
                        })
        if not recommendations:
            raise NoBreedingCombinationsError(target_species)
        
        recommendations.sort(key=lambda x: x["success_rate"], reverse=True)
        return recommendations

    def find_pairs_transient(
        self, inventory: List, target_species: str, desired_passives: List[str], require_clean: bool
    ) -> List[Dict]:
        """Calculates breeding probabilities for local guest/transient inventories."""
        target_pairs = self.reverse_lookup.get(target_species, set())
        if not target_pairs or not inventory:
            return []

        def get_attr(item, key):
            if isinstance(item, dict):
                val = item.get(key)
            else:
                val = getattr(item, key, None)
            if hasattr(val, "value"):
                return val.value
            return val

        def clean_str(val):
            return str(val or "").strip().upper()

        males = [p for p in inventory if clean_str(get_attr(p, 'gender')) in ['MALE', 'M']]
        females = [p for p in inventory if clean_str(get_attr(p, 'gender')) in ['FEMALE', 'F']]

        results = []

        for male in males:
            male_species = get_attr(male, 'species_name') or get_attr(male, 'species')
            male_passives = get_attr(male, 'passives') or []

            for female in females:
                female_species = get_attr(female, 'species_name') or get_attr(female, 'species')
                female_passives = get_attr(female, 'passives') or []

                pair_key = tuple(sorted([str(male_species), str(female_species)]))

                if pair_key not in target_pairs:
                    continue

                actual_child = calculate_child(
                    str(male_species), str(female_species), self.pals_data, self.unique_combos,
                    male_name=str(male_species)
                )
                if actual_child != target_species:
                    continue

                stats = self._calculate_stats_safely(
                    male_passives, female_passives, desired_passives, require_clean
                )

                rate = stats.get("success_rate", 0)

                if rate > 0:
                    results.append({
                        "male_parent": self._normalize_parent(male),
                        "female_parent": self._normalize_parent(female),
                        "child_species": target_species,
                        **stats
                    })

        results.sort(key=lambda x: x.get("success_rate", 0), reverse=True)
        return results