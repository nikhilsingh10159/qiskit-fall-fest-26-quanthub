"""Run stress test on solver.py with doubled noise."""
from run_full_validation import evaluate_solver

print("============================================================")
print("STRESS TEST: DOUBLED NOISE (8% misfire, 4% readout flip)")
print("============================================================")
res_stress = evaluate_solver(num_trials_per_family=10, misfire_prob=0.08, readout_flip_prob=0.04)
