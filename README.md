# Quantum Oracle Forensics

**Identifying the Hidden Structure of Sealed Quantum Black Boxes**  
IBM Qiskit Fall Fest 2026 | QC@IITI · IIT Indore | Industry Challenge by QryptoNox

**Team Name:** Quanthub  
**Team Members:** Aniket Gurjar, Ruchika Patil, Nikhil Singh, Amit Dubey  
**Repository:**(https://github.com/nikhilsingh10159/qiskit-fall-fest-26-quanthub.git) 
**Submission Tag:** `v1.0`  

---

## Overview

This repository provides an end-to-end adaptive quantum query solver for identifying sealed quantum black-box oracles and extracting their cryptographic secrets under hardware noise (4% oracle misfires, 2% readout bit flips, and doubled stress noise) within a strict budget of **60 queries**.

The solver identifies all 8 target families:
- **$m = 8$ outputs**: `simon`, `simon2`, `perm`
- **$m = 1$ outputs**: `constant`, `linear`, `grover`, `balanced`, `randfun`

---

## Repository Structure

```
├── solver.py               # Required submission file: solve(n, m, budget, families, run)
├── requirements.txt        # Package dependencies (qiskit 2.x, numpy, scipy)
├── REPORT.md               # 3-page Technical Report (math, decisions, baselines, failure modes)
├── AI_DISCLOSURE.md        # Official 1-page AI-use disclosure
├── test_logs.txt           # Comprehensive execution logs of all benchmarks and validations
├── test_runner.py          # Oracle generator and automated test runner
├── circuit_builders.py     # Qiskit circuit templates (Simon, BV, Grover, Classical)
├── oracle_sim.py           # Exact quantum simulator implementing hardware noise model
├── generate_all_logs.py    # Master runner reproducing all diagnostics and test_logs.txt
├── run_full_validation.py  # Validation harness testing 80 unseen oracles (Standard noise)
├── run_stress_test.py      # Validation harness testing 80 unseen oracles (Doubled noise)
└── benchmarks.py           # Compares 5 required baselines and budget scaling curves
```

---

## Quickstart & Reproduction

### 1. Installation
Install the required dependencies:
```bash
pip install -r requirements.txt
```

### 2. Verify Against Reference Examples
Run the reference check script to verify the simulator and solver against the public check values:
```bash
python test_reference_examples.py
```

### 3. Run the Master Benchmark Suite
To regenerate the full benchmark logs (`test_logs.txt`), including the 80-oracle evaluation, stress test, baseline comparisons, and budget diagnostic curves:
```bash
python generate_all_logs.py
```

---

## Execution Interface
- **File**: `solver.py`
- **Entrypoint**: `solve(n, m, budget, families, run)`
- **Return Type**: `(family, secret)`
  - `balanced`, `randfun`, `perm` return `(family, None)`
  - `constant` returns `('constant', c)` with $c \in \{0, 1\}$
  - `linear` returns `('linear', [a, b])` with $a \in [1, 255], b \in \{0, 1\}$
  - `grover` returns `('grover', t)` with $t \in [0, 255]$
  - `simon` returns `('simon', s)` with $s \in [1, 255]$
  - `simon2` returns `('simon2', [h1, h2, h3])` with $h_1 < h_2 < h_3$
- **Resource Constraints**: $\le 20$ qubits, $\le 60$ queries per oracle, CPU only, no external file access or network calls.
