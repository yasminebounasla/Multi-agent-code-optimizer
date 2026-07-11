
def run(n: int):
    data = [i % (n // 2) for i in range(n)]
    seen = set()
    duplicates = set()
    for num in data:
        if num in seen:
            duplicates.add(num)
        seen.add(num)
    return sorted(duplicates)
