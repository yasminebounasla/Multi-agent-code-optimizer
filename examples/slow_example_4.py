"""
Example 4: finding common elements between two lists using a nested loop
(checking membership via 'in' on a list is O(n) each time -> O(n*m) total).
Optimization target: convert one list to a set for O(1) average lookup.
"""


def run(n: int):
    list_a = list(range(n))
    list_b = list(range(n // 2, n + n // 2))

    common = []
    for item in list_a:
        if item in list_b:  # O(n) membership check on a list
            common.append(item)

    return sorted(common)


if __name__ == "__main__":
    print(run(3000)[:10])