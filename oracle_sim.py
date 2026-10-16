"""Prototype solver implementation and validation test."""
import time
import random
import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit import Gate

class OracleSimulator:
    """Exact, fast simulator for testing quantum oracle circuits."""
    def __init__(self, f, n=8, m=1, misfire_prob=0.04, readout_flip_prob=0.02):
        self.f = f
        self.n = n
        self.m = m
        self.misfire_prob = misfire_prob
        self.readout_flip_prob = readout_flip_prob
        self.query_count = 0

    def run(self, circuit: QuantumCircuit, shots: int = 1):
        num_oracle_calls = sum(1 for inst in circuit.data if inst.operation.name == "oracle")
        self.query_count += num_oracle_calls * shots
        if self.query_count > 60:
            raise RuntimeError(f"Exceeded query budget: {self.query_count} > 60")

        # Simulate circuit execution
        # Check circuit type for fast specialized execution or general execution
        counts = {}
        for _ in range(shots):
            out_bits = self._execute_shot(circuit)
            counts[out_bits] = counts.get(out_bits, 0) + 1
        return counts

    def _execute_shot(self, qc: QuantumCircuit):
        # We simulate the specific circuit patterns used by our solver:
        # Pattern 1: Classical query (X gates on some inputs, oracle, measure outputs)
        # Pattern 2: Bernstein-Vazirani (H on inputs, X+H on target, oracle, H on inputs, measure inputs)
        # Pattern 3: Simon (H on inputs, target=0, oracle, H on inputs, measure inputs)
        # Pattern 4: Grover (H on inputs, X+H on target, R iterations of [oracle, diffusion], measure inputs)

        # Check if it's a classical query circuit
        ops = [inst.operation.name for inst in qc.data]
        is_classical = all(op in ("x", "oracle", "measure") for op in ops)

        if is_classical:
            # Determine input x from X gates applied to input qubits
            x = 0
            for inst in qc.data:
                if inst.operation.name == "x":
                    q_idx = qc.find_bit(inst.qubits[0]).index
                    if q_idx < self.n:
                        x |= (1 << q_idx)
            
            # Oracle action
            if np.random.rand() < self.misfire_prob:
                out_val = 0 # misfire acts as identity, output qubits were initialized to 0
            else:
                out_val = self.f(x)
            
            # Readout noise on measured output bits
            # Find measured bits
            clbits = [0] * qc.num_clbits
            for inst in qc.data:
                if inst.operation.name == "measure":
                    q_idx = qc.find_bit(inst.qubits[0]).index
                    c_idx = qc.find_bit(inst.clbits[0]).index
                    bit = (out_val >> (q_idx - self.n)) & 1
                    if np.random.rand() < self.readout_flip_prob:
                        bit ^= 1
                    clbits[c_idx] = bit
            return "".join(str(clbits[i]) for i in reversed(range(qc.num_clbits)))

        # If it's BV circuit
        is_bv = ops.count("oracle") == 1 and ops.count("h") == 2 * self.n + 1 and "mcx" not in ops
        if is_bv:
            if np.random.rand() < self.misfire_prob:
                # Oracle misfire -> measured state is 0
                y = 0
            else:
                # BV sampling from distribution P(y) = |Fhat(y)|^2
                # Since n=8 is 256 states, we can evaluate exact amplitudes:
                x_vals = np.arange(256)
                fx_vals = np.array([self.f(x) for x in x_vals], dtype=int)
                # Walsh-Hadamard transform of (-1)^f(x)
                sign_fx = 1 - 2 * fx_vals
                # Fast Walsh-Hadamard Transform
                fhat = sign_fx.astype(float)
                h = 1
                while h < 256:
                    for i in range(0, 256, h * 2):
                        for j in range(i, i + h):
                            u = fhat[j]
                            v = fhat[j + h]
                            fhat[j] = u + v
                            fhat[j + h] = u - v
                    h *= 2
                fhat /= 256.0
                probs = fhat ** 2
                probs /= np.sum(probs)
                y = np.random.choice(256, p=probs)
            
            # Apply readout noise
            clbits = [0] * self.n
            for k in range(self.n):
                bit = (y >> k) & 1
                if np.random.rand() < self.readout_flip_prob:
                    bit ^= 1
                clbits[k] = bit
            return "".join(str(clbits[i]) for i in reversed(range(self.n)))

        # If it's Simon circuit
        is_simon = self.m == 8 and ops.count("oracle") == 1 and ops.count("h") == 2 * self.n and "x" not in ops
        if is_simon:
            if np.random.rand() < self.misfire_prob:
                y = 0
            else:
                # Sample uniform random x0
                x0 = np.random.randint(256)
                fx0 = self.f(x0)
                # Fiber F = {x : f(x) == fx0}
                # Fiber size is either 1 (perm), 2 (simon), 4 (simon2)
                # State after oracle on fiber: 1/sqrt(|F|) sum_{x in F} |x>
                # After H^8: amplitude of y is 1/(16 sqrt(|F|)) sum_{x in F} (-1)^{x . y}
                # For Simon: s . y == 0 mod 2
                # We can sample y directly:
                fiber = [x for x in range(256) if self.f(x) == fx0]
                K = len(fiber)
                # Amplitudes over all 256 y's
                amps = np.zeros(256, dtype=complex)
                for x in fiber:
                    for y_idx in range(256):
                        dot = bin(x & y_idx).count('1') % 2
                        amps[y_idx] += (1.0 if dot == 0 else -1.0)
                probs = np.abs(amps) ** 2
                probs /= np.sum(probs)
                y = np.random.choice(256, p=probs)

            clbits = [0] * self.n
            for k in range(self.n):
                bit = (y >> k) & 1
                if np.random.rand() < self.readout_flip_prob:
                    bit ^= 1
                clbits[k] = bit
            return "".join(str(clbits[i]) for i in reversed(range(self.n)))

        # If it's Grover circuit
        is_grover = ops.count("oracle") >= 2 or "mcx" in ops
        if is_grover:
            # Full Grover statevector evolution on 256 states
            psi = np.ones(256, dtype=float) / 16.0 # |s>
            R = ops.count("oracle")
            for it in range(R):
                # Oracle
                if np.random.rand() >= self.misfire_prob:
                    # (-1)^f(x)
                    for x in range(256):
                        if self.f(x) == 1:
                            psi[x] = -psi[x]
                # Diffusion: 2|s><s| - I
                mean_amp = np.mean(psi)
                psi = 2.0 * mean_amp - psi

            probs = np.abs(psi) ** 2
            probs /= np.sum(probs)
            y = np.random.choice(256, p=probs)
            clbits = [0] * self.n
            for k in range(self.n):
                bit = (y >> k) & 1
                if np.random.rand() < self.readout_flip_prob:
                    bit ^= 1
                clbits[k] = bit
            return "".join(str(clbits[i]) for i in reversed(range(self.n)))

        raise ValueError(f"Unknown circuit pattern: {ops[:10]}")

print("Simulator class ready.")
