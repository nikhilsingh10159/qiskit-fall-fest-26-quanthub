"""Run full validation suite on solver.py."""
import time
import random
import numpy as np
from oracle_sim import OracleSimulator
from test_runner import generate_oracle
from solver import solve

def evaluate_solver(num_trials_per_family=10, misfire_prob=0.04, readout_flip_prob=0.02):
    families_m1 = ["constant", "balanced", "linear", "grover", "randfun"]
    families_m8 = ["simon", "simon2", "perm"]
    all_families = families_m1 + families_m8

    total = 0
    correct = 0
    queries_correct = []
    family_results = {}
    confusion_matrix = {f_true: {f_pred: 0 for f_pred in all_families} for f_true in all_families}

    for fam in all_families:
        fam_correct = 0
        fam_queries = []
        fams_arg = families_m1 if fam in families_m1 else families_m8
        for i in range(num_trials_per_family):
            f_func, expected, m = generate_oracle(fam)
            sim = OracleSimulator(f_func, n=8, m=m, misfire_prob=misfire_prob, readout_flip_prob=readout_flip_prob)
            try:
                pred_fam, pred_sec = solve(8, m, 60, fams_arg, sim.run)
                used = sim.query_count
                is_correct = (pred_fam == expected[0]) and (pred_sec == expected[1])
                confusion_matrix[fam][pred_fam] += 1
                if is_correct:
                    fam_correct += 1
                    correct += 1
                    queries_correct.append(used)
                    fam_queries.append(used)
                else:
                    print(f"FAILED {fam} #{i+1}: expected {expected}, got ({pred_fam}, {pred_sec}) [q={used}]")
                total += 1
            except Exception as e:
                print(f"ERROR {fam} #{i+1}: {e}")
                confusion_matrix[fam]["error"] = confusion_matrix[fam].get("error", 0) + 1
                total += 1

        avg_q = np.mean(fam_queries) if fam_queries else 0
        family_results[fam] = {
            "correct": fam_correct,
            "total": num_trials_per_family,
            "acc": fam_correct / num_trials_per_family,
            "avg_queries": avg_q
        }
        print(f"Family {fam:10s}: {fam_correct:2d}/{num_trials_per_family} ({fam_correct/num_trials_per_family*100:5.1f}%) | Avg Queries: {avg_q:4.1f}")

    acc = correct / total
    worst_acc = min(r["acc"] for r in family_results.values())
    query_saving = np.mean([1.0 - q / 60.0 for q in queries_correct]) if queries_correct else 0

    print("\n" + "="*60)
    print(f"Overall Accuracy:       {correct}/{total} ({acc*100:.1f}%)")
    print(f"Worst-Family Accuracy:  {worst_acc*100:.1f}%")
    print(f"Mean Queries (Correct): {np.mean(queries_correct):.1f} / 60")
    print(f"Query Saving:           {query_saving*100:.1f}%")
    print("="*60)
    return {
        "accuracy": acc,
        "worst_accuracy": worst_acc,
        "query_saving": query_saving,
        "family_results": family_results,
        "confusion_matrix": confusion_matrix
    }

if __name__ == "__main__":
    print("Evaluating solver under normal noise (4% misfire, 2% readout flip)...")
    evaluate_solver(num_trials_per_family=10, misfire_prob=0.04, readout_flip_prob=0.02)
