"""Master test runner to generate comprehensive logs for test_logs.txt."""
import sys
import time
import io
import numpy as np

output_buffer = io.StringIO()

class Tee:
    def __init__(self, *files):
        self.files = files
    def write(self, obj):
        for f in self.files:
            f.write(obj)
            f.flush()
    def flush(self):
        for f in self.files:
            f.flush()

tee = Tee(sys.stdout, output_buffer)
sys.stdout = tee

print("="*80)
print("QUANTUM ORACLE FORENSICS: COMPREHENSIVE TEST SUITE AND DIAGNOSTICS")
print("IBM Qiskit Fall Fest 2026 | QC@IITI | Industry Challenge by QryptoNox")
print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
print("="*80)

# 1. Public Reference Instance Verification
print("\n[PART 1] Verifying Public Reference Examples...")
from test_reference_examples import f_linear, f_simon, f_simon2, f_perm, f_grover, f_constant
from oracle_sim import OracleSimulator
from solver import solve

ref_checks = [
    ("linear (a=178, b=1)", f_linear, 1, ["linear", "constant", "balanced", "grover", "randfun"], ("linear", [178, 1])),
    ("simon (s=105)", f_simon, 8, ["simon", "simon2", "perm"], ("simon", 105)),
    ("simon2 (H=[15, 49, 62])", f_simon2, 8, ["simon", "simon2", "perm"], ("simon2", [15, 49, 62])),
    ("perm (37x + 11 mod 256)", f_perm, 8, ["simon", "simon2", "perm"], ("perm", None)),
    ("grover (t=173)", f_grover, 1, ["linear", "constant", "balanced", "grover", "randfun"], ("grover", 173)),
    ("constant (c=1)", f_constant, 1, ["linear", "constant", "balanced", "grover", "randfun"], ("constant", 1)),
]

ref_passed = 0
for name, f_ref, m_ref, fams, expected in ref_checks:
    sim = OracleSimulator(f_ref, n=8, m=m_ref, misfire_prob=0.04, readout_flip_prob=0.02)
    pred_fam, pred_sec = solve(8, m_ref, 60, fams, sim.run)
    is_ok = (pred_fam == expected[0]) and (pred_sec == expected[1])
    if is_ok:
        ref_passed += 1
        print(f"  [PASS] {name:30s} -> Predicted: ({pred_fam}, {pred_sec}) | Queries: {sim.query_count}")
    else:
        print(f"  [FAIL] {name:30s} -> Expected: {expected}, Got: ({pred_fam}, {pred_sec})")

print(f"Reference Examples Result: {ref_passed}/{len(ref_checks)} passed.")

# 2. Full Validation on 80 Unseen Oracles (Standard Noise)
print("\n[PART 2] Running 80-Oracle Evaluation under Standard Noise (4% misfire, 2% readout flip)...")
from run_full_validation import evaluate_solver
res_std = evaluate_solver(num_trials_per_family=10, misfire_prob=0.04, readout_flip_prob=0.02)

# 3. Stress Noise Evaluation (Doubled Noise)
print("\n[PART 3] Running 80-Oracle Evaluation under Stress Noise (8% misfire, 4% readout flip)...")
res_stress = evaluate_solver(num_trials_per_family=10, misfire_prob=0.08, readout_flip_prob=0.04)

# 4. Strategy Baseline Comparison
print("\n[PART 4] Evaluating Strategy Baselines...")
from benchmarks import (
    solve_classical_only,
    solve_single_algorithm,
    solve_random_guessing,
    solve_non_adaptive,
    benchmark_strategy
)
res_adaptive = benchmark_strategy(solve, "Adaptive Solver (Ours)", num_per_family=8, budget=60)
res_classical = benchmark_strategy(solve_classical_only, "Classical-Only Strategy", num_per_family=8, budget=60)
res_single = benchmark_strategy(solve_single_algorithm, "Single-Algorithm Strategy", num_per_family=8, budget=60)
res_non_adaptive = benchmark_strategy(solve_non_adaptive, "Non-Adaptive Strategy", num_per_family=8, budget=60)
res_random = benchmark_strategy(solve_random_guessing, "Random Guessing Baseline", num_per_family=8, budget=60)

# 5. Budget Diagnostics (20, 30, 40, 50, 60)
print("\n[PART 5] Evaluating Accuracy as a Function of Query Budget...")
budget_stats = {}
for b in [20, 30, 40, 50, 60]:
    acc, worst_acc, avg_q, _ = benchmark_strategy(solve, f"Budget = {b:2d}", num_per_family=8, budget=b)
    budget_stats[b] = (acc, worst_acc, avg_q)

# 6. Confusion Matrix
print("\n[PART 6] Confusion Matrix (from Standard Noise Run):")
all_fams = ["constant", "balanced", "linear", "grover", "randfun", "simon", "simon2", "perm"]
cm = res_std["confusion_matrix"]
header = f"{'True \ Pred':12s} | " + " | ".join(f"{f[:5]:5s}" for f in all_fams)
print(header)
print("-" * len(header))
for true_f in all_fams:
    row = f"{true_f:12s} | " + " | ".join(f"{cm[true_f].get(pred_f, 0):5d}" for pred_f in all_fams)
    print(row)

print("\n" + "="*80)
print("ALL DIAGNOSTICS AND VALIDATIONS COMPLETE.")
print("="*80)

# Save to test_logs.txt
sys.stdout = sys.__stdout__
with open("test_logs.txt", "w", encoding="utf-8") as f:
    f.write(output_buffer.getvalue())

print("Saved output to test_logs.txt")
