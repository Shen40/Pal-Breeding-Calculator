import math
from typing import List, Set, Dict

class PassiveInheritanceEngine:
    INHERIT_PROBS  = {1: 0.4, 2: 0.3, 3: 0.2, 4: 0.1}
    NO_MUTATION_PROB = 0.4

    @staticmethod
    def _comb(n: int, k: int)->int:
        if k<0 or k>n:
            return 0
        return math.comb(n,k)

    @classmethod
    def calculate_exact_target_prob(
        cls, 
        parent_a: List[str], 
        parent_b: List[str], 
        desired_passive: List[str], 
        require_clean: bool = True
        )-> Dict[str, float]:

        # Calculate the exact probability of producting a child with desired passives

        pool: Set[str] = set(parent_a).union(set(parent_b))
        targets: Set[str] = set(desired_passive)

        k = len(pool)
        m = len(targets)

        if m == 0 or m>4:
            raise ValueError("Target passive must be between 1 and 4")

        # Target must be a subset of available parent passives 
        if not targets.issubset(pool):
            return {
                "success_rate": 0.0,
                "expected_eggs": float("inf"),
                "p95_eggs": float("inf"),
                "unique_parent_passives": k 
            }

        total_prob = 0

        for n, p_n in cls.INHERIT_PROBS.items():
            # Drawing n passives from a pool of only k is impossible when n > k;
            # that term simply contributes 0 probability (not a division error).
            denom = cls._comb(k, n)
            if denom == 0:
                continue

            if m == 4:
                if n == 4:
                    draw_prob = cls._comb(k-4, 4-4) / denom
                    total_prob += p_n * draw_prob
            else:
                if n<m:
                    continue

                # Probability of picking all m target passives in n draws from k pool
                # k-m choose n-m / k choose n for n >= m
                draw_prob = cls._comb(k-m, n-m)/ denom

                if require_clean:
                    # exactly m inherited and 0 mutations
                    if n == m:
                        clean_prob = 1.0 if n == 4 else cls.NO_MUTATION_PROB
                        total_prob += p_n * draw_prob * clean_prob
                else:
                    total_prob += p_n * draw_prob

        # Expected eggs = 1/p (Geometric distribution)
        expected_eggs = (1.0/ total_prob) if total_prob > 0 else float("inf")

        # 95% Confidence egg count: 1 - (1-p)^n >= 0.95 => N = ceil(ln(0.05)/ln(1-p))
        if 0.0 < total_prob < 1.0:
            p95_eggs = math.ceil(math.log(0.05)/math.log(1.0-total_prob))
        elif total_prob >= 1.0:
            p95_eggs = 1
        else:
            p95_eggs = float("inf")

        return{
            "success_rate": round(total_prob, 6),
            "percentage": f"{round(total_prob*100, 3)}%",
            "expected_eggs": int(round(expected_eggs, 1)),
            "p95_eggs": p95_eggs,
            "unique_parent_passives": k 
        }
