"""
Example 1: find duplicate numbers in a list using a naive O(n^2) nested loop.
An obvious optimization target: use a set/dict for O(n) lookup instead.
"""


def run(n: int):
    data = [i % (n // 2) for i in range(n)]  # guarantees duplicates exist

    duplicates = []
    for i in range(len(data)):
        for j in range(i + 1, len(data)):
            if data[i] == data[j] and data[i] not in duplicates:
                duplicates.append(data[i])

    return sorted(duplicates)


if __name__ == "__main__":
    print(run(2000))