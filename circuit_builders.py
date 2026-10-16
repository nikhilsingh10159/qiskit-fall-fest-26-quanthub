"""Comprehensive test of solver against all 8 families."""
import random
import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit import Gate
from oracle_sim import OracleSimulator

def build_classical_query_circuit(x, n, m):
    qc = QuantumCircuit(n + m, m)
    for k in range(n):
        if (x >> k) & 1:
            qc.x(k)
    qc.append(Gate("oracle", n + m, []), range(n + m))
    qc.measure(range(n, n + m), range(m))
    return qc

def build_bv_circuit(n):
    qc = QuantumCircuit(n + 1, n)
    qc.h(range(n))
    qc.x(n)
    qc.h(n)
    qc.append(Gate("oracle", n + 1, []), range(n + 1))
    qc.h(range(n))
    qc.measure(range(n), range(n))
    return qc

def build_simon_circuit(n, m):
    qc = QuantumCircuit(n + m, n)
    qc.h(range(n))
    qc.append(Gate("oracle", n + m, []), range(n + m))
    qc.h(range(n))
    qc.measure(range(n), range(n))
    return qc

def build_grover_circuit(n, iterations):
    qc = QuantumCircuit(n + 1, n)
    qc.h(range(n))
    qc.x(n)
    qc.h(n)
    for _ in range(iterations):
        qc.append(Gate("oracle", n + 1, []), range(n + 1))
        qc.h(range(n))
        qc.x(range(n))
        qc.h(n - 1)
        qc.mcx(list(range(n - 1)), n - 1)
        qc.h(n - 1)
        qc.x(range(n))
        qc.h(range(n))
    qc.measure(range(n), range(n))
    return qc

print("Circuit builder helpers compiled.")
