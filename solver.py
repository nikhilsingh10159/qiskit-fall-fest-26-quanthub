"""Quantum Oracle Forensics Solver.
Identifies the hidden structure of sealed quantum black boxes across 8 families
using adaptive query allocation, GF(2) subspace estimation, and statistical hypothesis testing.
"""

import random
from typing import Dict, List, Tuple, Any, Optional
import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit import Gate

def _build_classical_query_circuit(x: int, n: int, m: int) -> QuantumCircuit:
    """Builds a classical query circuit evaluating f(x)."""
    qc = QuantumCircuit(n + m, m)
    for k in range(n):
        if (x >> k) & 1:
            qc.x(k)
    qc.append(Gate("oracle", n + m, []), range(n + m))
    qc.measure(range(n, n + m), range(m))
    return qc

def _build_bv_circuit(n: int) -> QuantumCircuit:
    """Builds Bernstein-Vazirani circuit for phase probing."""
    qc = QuantumCircuit(n + 1, n)
    qc.h(range(n))
    qc.x(n)
    qc.h(n)
    qc.append(Gate("oracle", n + 1, []), range(n + 1))
    qc.h(range(n))
    qc.measure(range(n), range(n))
    return qc

def _build_simon_circuit(n: int, m: int) -> QuantumCircuit:
    """Builds Simon circuit for finding linear orthogonal relations."""
    qc = QuantumCircuit(n + m, n)
    qc.h(range(n))
    qc.append(Gate("oracle", n + m, []), range(n + m))
    qc.h(range(n))
    qc.measure(range(n), range(n))
    return qc

def _build_grover_circuit(n: int, iterations: int) -> QuantumCircuit:
    """Builds Grover search circuit with R iterations and exact diffusion."""
    qc = QuantumCircuit(n + 1, n)
    qc.h(range(n))
    qc.x(n)
    qc.h(n)
    for _ in range(iterations):
        qc.append(Gate("oracle", n + 1, []), range(n + 1))
        # Diffusion operator: -(2|s><s| - I)
        qc.h(range(n))
        qc.x(range(n))
        qc.h(n - 1)
        qc.mcx(list(range(n - 1)), n - 1)
        qc.h(n - 1)
        qc.x(range(n))
        qc.h(range(n))
    qc.measure(range(n), range(n))
    return qc

def _query_classical_single(x: int, n: int, m: int, run_fn) -> int:
    """Single-shot query to f(x). Costs 1 query."""
    qc = _build_classical_query_circuit(x, n, m)
    counts = run_fn(qc, shots=1)
    bstr = list(counts.keys())[0]
    return int(bstr, 2)

def _query_classical_robust(x: int, n: int, m: int, run_fn, shots: int = 3) -> int:
    """Bitwise majority vote across shots to suppress readout and misfire noise."""
    qc = _build_classical_query_circuit(x, n, m)
    counts = run_fn(qc, shots=shots)
    bit_counts = [0] * m
    total_shots = sum(counts.values())
    for bstr, cnt in counts.items():
        for bit_idx in range(m):
            char = bstr[m - 1 - bit_idx]
            if char == '1':
                bit_counts[bit_idx] += cnt
    res = 0
    for bit_idx in range(m):
        if bit_counts[bit_idx] > total_shots / 2:
            res |= (1 << bit_idx)
    return res

def _gf2_gaussian_elimination(vectors: List[int], n: int = 8) -> Tuple[int, List[int], List[int]]:
    """
    Performs GF(2) Gaussian elimination on integer bitstrings in F_2^n.
    
    Returns:
        (rank, basis, nullspace)
        where:
            rank: integer dimension of row space over GF(2)
            basis: row echelon basis vectors
            nullspace: list of all non-zero vectors in F_2^n orthogonal to basis
    """
    basis = []
    for v in vectors:
        if v == 0:
            continue
        cur = v
        for b in basis:
            msb = b.bit_length() - 1
            if (cur >> msb) & 1:
                cur ^= b
        if cur > 0:
            basis.append(cur)
            basis.sort(key=lambda x: x.bit_length(), reverse=True)

    rank = len(basis)
    nullspace = []
    for cand in range(1, 1 << n):
        if all(bin(cand & b).count('1') % 2 == 0 for b in basis):
            nullspace.append(cand)

    return rank, basis, nullspace

def solve(n: int, m: int, budget: int, families: List[str], run) -> Tuple[str, Any]:
    """
    Identifies the oracle family and extracts its secret.
    
    Args:
        n: Number of input qubits (8)
        m: Number of output qubits (1 or 8)
        budget: Maximum total queries (<= 60)
        families: List of candidate family names
        run: Callable run(circuit, shots) returning Qiskit counts dictionary
        
    Returns:
        (family, secret) tuple
    """
    queries_used = [0]

    def tracked_run(qc: QuantumCircuit, shots: int = 1) -> Dict[str, int]:
        num_oracle = sum(1 for inst in qc.data if inst.operation.name == "oracle")
        cost = num_oracle * shots
        if queries_used[0] + cost > budget:
            raise RuntimeError(f"Budget exceeded: {queries_used[0]} + {cost} > {budget}")
        queries_used[0] += cost
        return run(qc, shots=shots)

    # =========================================================================
    # CASE 1: m = 8 (Families: simon, simon2, perm)
    # GF(2) Noise Filter with Frequency Filtering & Rank/Null Space
    # =========================================================================
    if m == 8:
        # Run Simon circuit with majority of budget (leaving margin for verification if needed)
        shots_simon = min(52, budget)
        qc_simon = _build_simon_circuit(n, m)
        counts = tracked_run(qc_simon, shots=shots_simon)

        # Frequency filter: tally measured 8-bit strings and discard count == 1
        filtered_vectors = [
            int(bstr, 2)
            for bstr, cnt in counts.items()
            if cnt > 1 and int(bstr, 2) != 0
        ]

        # Perform GF(2) Gaussian elimination on remaining filtered vectors
        rank, basis, nullspace = _gf2_gaussian_elimination(filtered_vectors, n=n)

        # If rank is 7, classify as simon and calculate the 1D null space to return secret shift
        if rank == 7 and len(nullspace) >= 1:
            return ("simon", nullspace[0])

        # If rank is 6, classify as simon2 and find 3 non-zero elements of 2D null space, returning them in ascending order
        elif rank == 6 and len(nullspace) >= 3:
            # If queries remain, quickly verify if 3 match (simon2) or only 1 matches (simon)
            if budget - queries_used[0] >= 4:
                v0 = _query_classical_single(0, n, m, tracked_run)
                matches = [h for h in nullspace[:3] if _query_classical_single(h, n, m, tracked_run) == v0]
                if len(matches) == 1:
                    return ("simon", matches[0])
            return ("simon2", sorted(nullspace[:3]))

        # If it remains rank 8, classify as perm (returning None for secret)
        elif rank >= 8:
            return ("perm", None)

        # Rank < 6: fall back to classical verification of candidates in nullspace
        else:
            if len(nullspace) > 0 and budget - queries_used[0] >= 4:
                v0 = _query_classical_single(0, n, m, tracked_run)
                matches = [h for h in nullspace[:7] if budget - queries_used[0] > 0 and _query_classical_single(h, n, m, tracked_run) == v0]
                if len(matches) >= 3:
                    return ("simon2", sorted(matches[:3]))
                elif len(matches) == 1:
                    return ("simon", matches[0])
                elif len(matches) == 2:
                    h1, h2 = matches[0], matches[1]
                    return ("simon2", sorted([h1, h2, h1 ^ h2]))
            return ("perm", None)

    # =========================================================================
    # CASE 2: m = 1 (Families: constant, linear, grover, balanced, randfun)
    # =========================================================================
    else:
        # Step 1: Bernstein-Vazirani probe (8 shots)
        shots_bv = min(8, max(4, int(budget * 0.15)))
        qc_bv = _build_bv_circuit(n)
        counts_bv = tracked_run(qc_bv, shots=shots_bv)

        int_counts = {}
        for bstr, cnt in counts_bv.items():
            val = int(bstr, 2)
            int_counts[val] = int_counts.get(val, 0) + cnt

        sorted_bv = sorted(int_counts.items(), key=lambda item: item[1], reverse=True)
        top_val, top_cnt = sorted_bv[0]
        zero_cnt = int_counts.get(0, 0)

        # Test A: Linear function
        cand_linear_a = None
        if "linear" in families:
            if top_val != 0 and top_cnt >= 2:
                cand_linear_a = top_val
            elif len(sorted_bv) >= 2 and sorted_bv[1][0] != 0 and sorted_bv[1][1] >= 2:
                cand_linear_a = sorted_bv[1][0]
            elif top_val != 0 and top_cnt == 1:
                for other_val, _ in sorted_bv[1:]:
                    if other_val != 0 and bin(top_val ^ other_val).count('1') <= 1:
                        cand_linear_a = top_val
                        break

        if cand_linear_a is not None and (budget - queries_used[0] >= 11):
            cand_a = cand_linear_a
            b = _query_classical_robust(0, n, m, tracked_run, shots=3)
            test_pts = random.sample(range(1, 256), 8)
            matches = 0
            for x in test_pts:
                exp = (bin(cand_a & x).count('1') % 2) ^ b
                obs = _query_classical_single(x, n, m, tracked_run)
                if obs == exp:
                    matches += 1
            if matches >= 6:
                return ("linear", [int(cand_a), int(b)])

        # Test B: Constant or Grover (high zero count in BV)
        if zero_cnt >= 3:
            probe_pts = random.sample(range(256), min(5, budget - queries_used[0]))
            probe_vals = [_query_classical_single(x, n, m, tracked_run) for x in probe_pts]
            if len(probe_vals) >= 4 and sum(probe_vals) >= len(probe_vals) - 1:
                extra_c1 = random.sample([x for x in range(256) if x not in probe_pts], min(2, budget - queries_used[0]))
                extra_vals = [_query_classical_single(x, n, m, tracked_run) for x in extra_c1]
                if sum(probe_vals) + sum(extra_vals) >= len(probe_vals) + len(extra_vals) - 1:
                    if "constant" in families:
                        return ("constant", 1)

            # Grover Search for single marked item t
            if "grover" in families:
                for R in [12, 11, 10]:
                    if budget - queries_used[0] < R + 4:
                        break
                    qc_gr = _build_grover_circuit(n, iterations=R)
                    res = tracked_run(qc_gr, shots=1)
                    cand_t = int(list(res.keys())[0], 2)
                    
                    if _query_classical_single(cand_t, n, m, tracked_run) == 1:
                        votes = 1
                        for _ in range(2):
                            if budget - queries_used[0] >= 1:
                                votes += _query_classical_single(cand_t, n, m, tracked_run)
                        if votes >= 2:
                            other_pt = (cand_t + 13) % 256
                            if _query_classical_single(other_pt, n, m, tracked_run) == 0:
                                return ("grover", cand_t)

            if "constant" in families and sum(probe_vals) == 0:
                rem = budget - queries_used[0]
                check_pts = random.sample([x for x in range(256) if x not in probe_pts], min(4, rem))
                if all(_query_classical_single(x, n, m, tracked_run) == 0 for x in check_pts):
                    return ("constant", 0)

        # =====================================================================
        # Test C: Balanced vs Randfun
        # Allocate classical queries with decision boundary at p = 0.37
        # =====================================================================
        rem_budget = budget - queries_used[0]
        K = min(rem_budget, 45)
        # Ensure at least 30 classical queries if budget permits
        K = max(min(30, rem_budget), K)

        if K > 0:
            sampled = random.sample(range(256), K)
            num_ones = sum(_query_classical_single(x, n, m, tracked_run) for x in sampled)
            fraction_ones = num_ones / K
            
            # Decision boundary at p = 0.37
            if fraction_ones >= 0.37:
                return ("balanced", None)
            else:
                return ("randfun", None)
        else:
            return (families[0], None)
