def run(n: int):
    reference = list(range(n, 0, -1))  # unsorted, reversed
    queries = list(range(0, n, 7))
    sorted_ref = sorted(reference)
    ref_dict = {x: i for i, x in enumerate(sorted_ref)}  # for faster indexing
    results = [ref_dict[q] for q in queries if q in ref_dict]
    return results

if __name__ == "__main__":
    print(run(1500)[:10])