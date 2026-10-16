"""Test runner and oracle generator module for Quantum Oracle Forensics."""

import random
from typing import Callable, Tuple, Any, List
import numpy as np
from oracle_sim import OracleSimulator
from solver import solve

def generate_oracle(family: str) -> Tuple[Callable[[int], int], Tuple[str, Any], int]:
    """
    Generates an oracle instance for a specified family.
    
    Returns:
        (f_func, expected_result, m)
        where:
            f_func: callable f(x) -> int
            expected_result: (family, secret) tuple
            m: number of output bits (1 or 8)
    """
    if family == "constant":
        c = random.choice([0, 1])
        return (lambda x: c), ("constant", c), 1

    elif family == "balanced":
        ones_set = set(random.sample(range(256), 128))
        return (lambda x: 1 if x in ones_set else 0), ("balanced", None), 1

    elif family == "linear":
        a = random.randint(1, 255)
        b = random.choice([0, 1])
        return (lambda x: (bin(a & x).count('1') % 2) ^ b), ("linear", [a, b]), 1

    elif family == "grover":
        t = random.randint(0, 255)
        return (lambda x: 1 if x == t else 0), ("grover", t), 1

    elif family == "randfun":
        table = [1 if random.random() < 0.3 else 0 for _ in range(256)]
        return (lambda x: table[x]), ("randfun", None), 1

    elif family == "simon":
        s = random.randint(1, 255)
        # 2-to-1: pair up {x, x ^ s}
        assigned = {}
        avail = list(range(256))
        random.shuffle(avail)
        val_idx = 0
        table = [0] * 256
        for x in range(256):
            if x not in assigned:
                val = avail[val_idx]
                val_idx += 1
                assigned[x] = val
                assigned[x ^ s] = val
                table[x] = val
                table[x ^ s] = val
        return (lambda x: table[x]), ("simon", s), 8

    elif family == "simon2":
        # 4-to-1: hidden 2D subspace H = {0, h1, h2, h3}
        h1 = random.randint(1, 255)
        h2 = random.randint(1, 255)
        while h2 == h1 or h2 == 0:
            h2 = random.randint(1, 255)
        h3 = h1 ^ h2
        H = sorted([h1, h2, h3])
        # Cosets of H
        assigned = {}
        avail = list(range(256))
        random.shuffle(avail)
        val_idx = 0
        table = [0] * 256
        for x in range(256):
            if x not in assigned:
                val = avail[val_idx]
                val_idx += 1
                for h in [0, H[0], H[1], H[2]]:
                    assigned[x ^ h] = val
                    table[x ^ h] = val
        return (lambda x: table[x]), ("simon2", H), 8

    elif family == "perm":
        perm = list(range(256))
        random.shuffle(perm)
        return (lambda x: perm[x]), ("perm", None), 8

    else:
        raise ValueError(f"Unknown family: {family}")

def run_tests(num_per_family: int = 5, misfire_prob: float = 0.04, readout_flip_prob: float = 0.02):
    """Runs tests on random oracles across all 8 families."""
    families_m1 = ["constant", "balanced", "linear", "grover", "randfun"]
    families_m8 = ["simon", "simon2", "perm"]
    all_families = families_m1 + families_m8

    total = 0
    correct = 0
    queries_correct = []

    print(f"Running test suite ({num_per_family} oracles per family)...")
    for fam in all_families:
        fam_correct = 0
        fam_queries = []
        fams_arg = families_m1 if fam in families_m1 else families_m8
        for i in range(num_per_family):
            f_func, expected, m = generate_oracle(fam)
            sim = OracleSimulator(f_func, n=8, m=m, misfire_prob=misfire_prob, readout_flip_prob=readout_flip_prob)
            try:
                pred_fam, pred_sec = solve(8, m, 60, fams_arg, sim.run)
                used = sim.query_count
                is_correct = (pred_fam == expected[0]) and (pred_sec == expected[1])
                if is_correct:
                    fam_correct += 1
                    correct += 1
                    queries_correct.append(used)
                    fam_queries.append(used)
                else:
                    print(f"  [FAIL] {fam} #{i+1}: expected {expected}, got ({pred_fam}, {pred_sec})")
                total += 1
            except Exception as e:
                print(f"  [ERROR] {fam} #{i+1}: {e}")
                total += 1

        avg_q = np.mean(fam_queries) if fam_queries else 0
        print(f"Family {fam:10s}: {fam_correct:2d}/{num_per_family} ({fam_correct/num_per_family*100:5.1f}%) | Avg Queries: {avg_q:4.1f}")

    acc = correct / total
    query_saving = np.mean([1.0 - q / 60.0 for q in queries_correct]) if queries_correct else 0
    print("\n" + "="*60)
    print(f"Overall Accuracy:       {correct}/{total} ({acc*100:.1f}%)")
    print(f"Mean Queries (Correct): {np.mean(queries_correct):.1f} / 60")
    print(f"Query Saving:           {query_saving*100:.1f}%")
    print("="*60)

if __name__ == "__main__":
    run_tests(num_per_family=5)
