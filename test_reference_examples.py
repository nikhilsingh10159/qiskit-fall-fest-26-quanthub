"""Test reference instances and permutation action of oracle."""
import numpy as np

# Reference test instances:
# 1. linear: a = 178, b = 1
def f_linear(x):
    # a = 178, b = 1
    # a.x = parity of bits shared by a and x
    a = 178
    b = 1
    shared = a & x
    parity = bin(shared).count('1') % 2
    return parity ^ b

print("--- Linear Checks ---")
print("f(0) =", f_linear(0), "expected 1")
print("f(1) =", f_linear(1), "expected 1")
print("f(2) =", f_linear(2), "expected 0")
print("f(255) =", f_linear(255), "expected 1")
assert f_linear(0) == 1 and f_linear(1) == 1 and f_linear(2) == 0 and f_linear(255) == 1

# 2. simon: s = 105, f(x) = min(x, x ^ s)
def f_simon(x):
    s = 105
    return min(x, x ^ s)

print("--- Simon Checks ---")
print("f(5) =", f_simon(5), "expected 5")
print("f(108) =", f_simon(108), "expected 5")
print("f(105) =", f_simon(105), "expected 0")
print("f(200) =", f_simon(200), "expected 161")
assert f_simon(5) == 5 and f_simon(108) == 5 and f_simon(105) == 0 and f_simon(200) == 161

# 3. simon2: H = {0, 15, 49, 62}, f(x) = min over h in H of (x ^ h)
def f_simon2(x):
    H = [0, 15, 49, 62]
    return min(x ^ h for h in H)

print("--- Simon2 Checks ---")
print("f(0), f(15), f(49), f(62) =", f_simon2(0), f_simon2(15), f_simon2(49), f_simon2(62), "expected 0 0 0 0")
print("f(1) =", f_simon2(1), "expected 1")
print("f(200) =", f_simon2(200), "expected 199")
assert f_simon2(0) == 0 and f_simon2(15) == 0 and f_simon2(49) == 0 and f_simon2(62) == 0
assert f_simon2(1) == 1 and f_simon2(200) == 199

# 4. perm: f(x) = (37x + 11) mod 256
def f_perm(x):
    return (37 * x + 11) % 256

print("--- Perm Checks ---")
print("f(0) =", f_perm(0), "expected 11")
print("f(1) =", f_perm(1), "expected 48")
print("f(2) =", f_perm(2), "expected 85")
print("f(255) =", f_perm(255), "expected 230")
assert f_perm(0) == 11 and f_perm(1) == 48 and f_perm(2) == 85 and f_perm(255) == 230

# 5. grover: t = 173
def f_grover(x):
    return 1 if x == 173 else 0

print("--- Grover Checks ---")
print("f(173) =", f_grover(173), "expected 1")
print("f(0) =", f_grover(0), "expected 0")
assert f_grover(173) == 1 and f_grover(0) == 0

# 6. constant: c = 1
def f_constant(x):
    return 1

print("--- Constant Checks ---")
print("f(0) =", f_constant(0), "expected 1")
print("f(100) =", f_constant(100), "expected 1")
assert f_constant(0) == 1 and f_constant(100) == 1

print("\nALL REFERENCE EXAMPLES MATCH EXACTLY!")
