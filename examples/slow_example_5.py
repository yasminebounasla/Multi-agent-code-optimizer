"""
Example 5: redundant repeated computation -- sorting the same reference list
inside a loop on every iteration, when it only needs to be sorted once.
Optimization target: hoist the invariant computation (sort) out of the loop.
"""


def run(n: int):
    reference = list(range(n, 0, -1))  # unsorted, reversed
    queries = list(range(0, n, 7))

    results = []
    for q in queries:
        sorted_ref = sorted(reference)  # recomputed every iteration, unnecessarily
        if q in sorted_ref:
            results.append(sorted_ref.index(q))

    return results


if __name__ == "__main__":
    print(run(1500)[:10])