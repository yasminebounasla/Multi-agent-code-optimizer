"""
Example 2: naive recursive Fibonacci with massive redundant recomputation.
Optimization target: memoization (cache) or iterative approach.
"""


def run(n: int):
    def fib(k):
        if k <= 1:
            return k
        return fib(k - 1) + fib(k - 2)

    return fib(n)


if __name__ == "__main__":
    print(run(28))