# AI Assistance Disclosure
**IBM Qiskit Fall Fest 2026 | QC@IITI · IIT Indore | Industry Challenge by QryptoNox**

**Team Name:** Quanthub  
**Team Members:** Aniket Gurjar, Ruchika Patil, Nikhil Singh, Amit Dubey
**Affiliation:** IIPS DAVV, Indore 

---

### Declaration of AI Tool Usage
In accordance with ethical AI usage and transparency standards, this document discloses all AI assistance utilized during the development of this project.

### 1. Tools and Models Used
- **Assistant / Platform**: Antigravity Assistant (powered by Google Gemini 3.8 Flash / Thinking models).
- **Environment**: Local command execution shell and IDE environment on Windows.

### 2. Specific Scope of Assistance
AI assistance was utilized for:
1. **Mathematical derivations & Statistical Modelling**:
   - Calculation of Walsh-Hadamard Fourier amplitudes $\hat{F}(y)$ for the 8 oracle families under uniform and delta state distributions.
   - Closed-form variance and expectation formulas for Binomial vs Hypergeometric testing under oracle misfire ($p_m$) and readout bit-flip ($p_r$) noise.
   - Derivation of the optimal Bayes decision boundary threshold $\tau = 0.389 \times K$ separating `randfun` and `balanced`.
2. **Circuit Synthesis & Qiskit 2.x API Alignment**:
   - Implementation of exact Grover diffusion operator circuits using native multi-controlled gate decompositions (`mcx` and single-qubit rotations).
   - Placement of the placeholder `Gate("oracle", n+m, [])` instructions in compliance with judges' substitution requirements.
3. **Benchmarking Harness & Automation**:
   - Authoring the Monte Carlo simulation harness (`oracle_sim.py`, `benchmarks.py`, `generate_all_logs.py`) to systematically test 80 unseen oracles across all required baseline scenarios.

### 3. Human Independent Verification and Mathematical Validation
- **No Hard-Coded Answers or Lookup Tables**: All decisions within `solver.py` are strictly derived from real-time quantum and classical measurement outputs produced by the `run(circuit, shots)` interface.
- **Reference Instance Check**: The simulator and solver were independently checked and validated against standard public reference test cases for `linear`, `simon`, `simon2`, `perm`, `grover`, and `constant`, confirming exact numerical concordance with all check values.
- **Error Budget Auditing**: The query counter logic and budget limits (60 queries max, CPU execution, $\le 20$ qubits) were verified to prevent disqualification.

---

