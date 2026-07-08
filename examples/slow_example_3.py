"""
Example 3: building a large string with += in a loop (O(n^2) due to string
immutability in Python -- each += creates a new string and copies everything).
Optimization target: build a list and use ''.join() instead.
"""


def run(n: int):
    result = ""
    for i in range(n):
        result += str(i) + ","
    return result


if __name__ == "__main__":
    print(run(20000)[:50])