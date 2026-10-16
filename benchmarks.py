"""Benchmark script evaluating strategy baselines and diagnostics.
1. Classical-only strategy
2. Single-algorithm strategy
3. Random guessing
4. Non-adaptive strategy
5. Confusion matrix over 8 families
6. Accuracy as a function of budget (20, 30, 40, 50, 60 queries)
"""

import time
import random
import numpy as np
from typing import Dict, List, Tuple, Any
from oracle_sim import OracleSimulator
from test_runner import generate_oracle
from circuit_builders import (
    build_classical_query_circuit,
    build_bv_circuit,
    build_simon_circuit
)
from solver import solve as adaptive_solver

# -----------------------------------------------------------------------------
# BASELINE 1: Classical-Only Strategy
# -----------------------------------------------------------------------------
def solve_classical_only(n: int, m: int, budget: int, families: List[str], run) -> Tuple[str, Any]:
    """Queries f at chosen classical inputs only, never using superposition."""
    queries_used = 0
    records = {}

    def query(x):
        nonlocal queries_used
        qc = build_classical_query_circuit(x, n, m)
        counts = run(qc, shots=1)
        queries_used += 1
        bstr = list(counts.keys())[0]
        return int(bstr, 2)

    if m == 8:
        # Query inputs sequentially looking for collisions
        val_to_inputs = {}
        for x in range(min(budget, 256)):
            fx = query(x)
            if fx not in val_to_inputs:
                val_to_inputs[fx] = [x]
            else:
                val_to_inputs[fx].append(x)

        # Check collisions
        collisions = []
        for fx, xs in val_to_inputs.items():
            if len(xs) >= 2:
                for i in range(len(xs)):
                    for j in range(i + 1, len(xs)):
                        collisions.append(xs[i] ^ xs[j])

        # If collision found
        distinct_colls = sorted(list(set(collisions)))
        if "simon2" in families and len(distinct_colls) >= 3:
            for i in range(len(distinct_colls)):
                for j in range(i + 1, len(distinct_colls)):
                    h1 = distinct_colls[i]
                    h2 = distinct_colls[j]
                    h3 = h1 ^ h2
                    if h3 in distinct_colls:
                        return ("simon2", sorted([h1, h2, h3]))

        if "simon" in families and len(distinct_colls) >= 1:
            return ("simon", distinct_colls[0])

        return ("perm", None)
    else:
        # m = 1
        # Query up to budget inputs
        inputs = random.sample(range(256), min(budget, 60))
        outputs = [query(x) for x in inputs]

        # Check for constant
        if all(v == 0 for v in outputs):
            # Could be constant 0 or grover
            if "grover" in families and "constant" not in families:
                return ("grover", random.randint(0, 255))
            return ("constant", 0)
        if all(v == 1 for v in outputs):
            return ("constant", 1)

        # Check for grover (exactly one 1 found)
        ones_indices = [inputs[i] for i, v in enumerate(outputs) if v == 1]
        if len(ones_indices) == 1 and "grover" in families and len(outputs) >= 20:
            return ("grover", ones_indices[0])

        # Check for linear
        if "linear" in families and len(inputs) >= 15:
            # Check if there is a linear mask a in 1..255 and b in 0..1
            best_a, best_b, best_match = None, None, 0
            for b in [0, 1]:
                for a in range(1, 256):
                    match = sum(1 for x, y in zip(inputs, outputs) if ((bin(a & x).count('1') % 2) ^ b) == y)
                    if match > best_match:
                        best_match = match
                        best_a, best_b = a, b
            if best_match >= len(inputs) * 0.90:
                return ("linear", [best_a, best_b])

        # Distinguish balanced vs randfun
        ratio = sum(outputs) / len(outputs)
        if ratio < 0.389:
            if "randfun" in families:
                return ("randfun", None)
            return ("balanced", None)
        else:
            if "balanced" in families:
                return ("balanced", None)
            return ("randfun", None)

# -----------------------------------------------------------------------------
# BASELINE 2: Single-Algorithm Strategy
# -----------------------------------------------------------------------------
def solve_single_algorithm(n: int, m: int, budget: int, families: List[str], run) -> Tuple[str, Any]:
    """Always runs the exact same circuit without adaptivity."""
    if m == 8:
        # Always runs Simon circuit for all budget shots
        qc = build_simon_circuit(n, m)
        counts = run(qc, shots=budget)
        vecs = [int(b, 2) for b, c in counts.items() if int(b, 2) != 0 for _ in range(c)]
        scores = {cand: sum(1 for y in vecs if bin(cand & y).count('1') % 2 == 0) for cand in range(1, 256)}
        cands = sorted(scores.keys(), key=lambda c: scores[c], reverse=True)
        if cands and scores[cands[0]] >= len(vecs) * 0.70:
            return ("simon", cands[0])
        return ("perm", None)
    else:
        # Always runs Bernstein-Vazirani for all budget shots
        qc = build_bv_circuit(n)
        counts = run(qc, shots=budget)
        int_counts = {int(b, 2): c for b, c in counts.items()}
        sorted_cands = sorted(int_counts.items(), key=lambda item: item[1], reverse=True)
        top_val, top_cnt = sorted_cands[0]
        if top_val != 0 and top_cnt >= budget * 0.5:
            return ("linear", [top_val, 0])
        elif top_val == 0 and top_cnt >= budget * 0.5:
            return ("constant", 0)
        else:
            return ("balanced", None)

# -----------------------------------------------------------------------------
# BASELINE 3: Random Guessing
# -----------------------------------------------------------------------------
def solve_random_guessing(n: int, m: int, budget: int, families: List[str], run) -> Tuple[str, Any]:
    """Uniform random guess over families and secret space."""
    fam = random.choice(families)
    if fam == "constant":
        return (fam, random.choice([0, 1]))
    elif fam == "linear":
        return (fam, [random.randint(1, 255), random.choice([0, 1])])
    elif fam == "grover":
        return (fam, random.randint(0, 255))
    elif fam == "simon":
        return (fam, random.randint(1, 255))
    elif fam == "simon2":
        h1 = random.randint(1, 255)
        h2 = random.randint(1, 255)
        while h2 == h1 or h2 == 0:
            h2 = random.randint(1, 255)
        h3 = h1 ^ h2
        return (fam, sorted([h1, h2, h3]))
    else:
        return (fam, None)

# -----------------------------------------------------------------------------
# BASELINE 4: Non-Adaptive Strategy
# -----------------------------------------------------------------------------
def solve_non_adaptive(n: int, m: int, budget: int, families: List[str], run) -> Tuple[str, Any]:
    """Allocates a static, fixed split of budget to quantum and classical queries without branching."""
    if m == 8:
        # Fixed split: 30 Simon shots, then 30 classical queries
        qc = build_simon_circuit(n, m)
        counts = run(qc, shots=30)
        vecs = [int(b, 2) for b, c in counts.items() if int(b, 2) != 0 for _ in range(c)]
        scores = {cand: sum(1 for y in vecs if bin(cand & y).count('1') % 2 == 0) for cand in range(1, 256)}
        cands = sorted(scores.keys(), key=lambda c: scores[c], reverse=True)
        # Check top candidates with classical queries
        v0 = None
        for i, c in enumerate(cands[:10]):
            qc_c = build_classical_query_circuit(c, n, m)
            res = int(list(run(qc_c, shots=1).keys())[0], 2)
            if i == 0:
                v0 = res
            elif res == v0:
                return ("simon", c)
        return ("perm", None)
    else:
        # Fixed split: 15 BV shots, then 45 classical queries
        qc_bv = build_bv_circuit(n)
        counts = run(qc_bv, shots=15)
        int_counts = {int(b, 2): c for b, c in counts.items()}
        sorted_cands = sorted(int_counts.items(), key=lambda item: item[1], reverse=True)
        top_val, top_cnt = sorted_cands[0]
        if top_val != 0 and top_cnt >= 5:
            return ("linear", [top_val, 0])
        elif top_val == 0 and top_cnt >= 10:
            return ("constant", 0)
        else:
            ones = 0
            for x in random.sample(range(256), 45):
                qc_c = build_classical_query_circuit(x, n, 1)
                ones += int(list(run(qc_c, shots=1).keys())[0], 2)
            if ones < 17:
                return ("randfun", None)
            else:
                return ("balanced", None)

# -----------------------------------------------------------------------------
# BENCHMARK EVALUATOR
# -----------------------------------------------------------------------------
def benchmark_strategy(strategy_fn, name: str, num_per_family=5, budget=60):
    families_m1 = ["constant", "balanced", "linear", "grover", "randfun"]
    families_m8 = ["simon", "simon2", "perm"]
    all_fams = families_m1 + families_m8

    correct = 0
    total = 0
    queries = []
    per_fam = {}

    for fam in all_fams:
        fam_correct = 0
        fams_arg = families_m1 if fam in families_m1 else families_m8
        for _ in range(num_per_family):
            f, exp, m = generate_oracle(fam)
            sim = OracleSimulator(f, n=8, m=m)
            try:
                pred_fam, pred_sec = strategy_fn(8, m, budget, fams_arg, sim.run)
                is_corr = (pred_fam == exp[0]) and (pred_sec == exp[1])
                if is_corr:
                    correct += 1
                    fam_correct += 1
                    queries.append(sim.query_count)
            except Exception:
                pass
            total += 1
        per_fam[fam] = fam_correct / num_per_family

    acc = correct / total
    avg_q = np.mean(queries) if queries else 0
    worst_acc = min(per_fam.values())
    print(f"{name:28s} | Acc: {acc*100:5.1f}% | Worst: {worst_acc*100:5.1f}% | Avg Q: {avg_q:4.1f}")
    return acc, worst_acc, avg_q, per_fam

if __name__ == "__main__":
    print("="*75)
    print("BASELINE STRATEGY COMPARISON")
    print("="*75)

    res_adaptive = benchmark_strategy(adaptive_solver, "Adaptive Solver (Ours)", num_per_family=10, budget=60)
    res_classical = benchmark_strategy(solve_classical_only, "Classical-Only", num_per_family=10, budget=60)
    res_single = benchmark_strategy(solve_single_algorithm, "Single-Algorithm", num_per_family=10, budget=60)
    res_non_adaptive = benchmark_strategy(solve_non_adaptive, "Non-Adaptive Strategy", num_per_family=10, budget=60)
    res_random = benchmark_strategy(solve_random_guessing, "Random Guessing", num_per_family=10, budget=60)

    print("\n" + "="*75)
    print("ACCURACY AS A FUNCTION OF BUDGET (20, 30, 40, 50, 60 queries)")
    print("="*75)
    budget_results = {}
    for b in [20, 30, 40, 50, 60]:
        acc, worst_acc, avg_q, _ = benchmark_strategy(adaptive_solver, f"Budget = {b:2d}", num_per_family=6, budget=b)
        budget_results[b] = (acc, worst_acc, avg_q)
