def run(n: int):
    result = []
    for i in range(n):
        result.append(str(i) + ',')
    return ''.join(result)

if __name__ == "__main__":
    print(run(20000)[:50])