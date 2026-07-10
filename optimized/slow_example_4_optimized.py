def run(n: int):
    set_a = set(range(n))
    set_b = set(range(n // 2, n + n // 2))

    common = sorted(list(set_a & set_b))

    return common

if __name__ == "__main__":
    print(run(3000)[:10])