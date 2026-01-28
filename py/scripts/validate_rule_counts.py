import subprocess
import sys


FILES = [
    "rules/adblockdns.txt",
    "rules/adblockdomain.txt",
    "rules/adblockfilters.txt",
]
MIN_RATIO = 0.7
MAX_RATIO = 1.5
MIN_ABS = 10000


def count_lines(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.strip())


def get_prev_count(path: str):
    result = subprocess.run(
        ["git", "show", "HEAD:%s" % path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        return None
    return count_lines(result.stdout)


def get_cur_count(path: str):
    try:
        with open(path, "r") as f:
            return count_lines(f.read())
    except Exception:
        return None


def is_anomalous(new_count: int, old_count: int) -> bool:
    if old_count is None or new_count is None:
        return False
    if old_count < 1000:
        return False
    diff = abs(new_count - old_count)
    if diff < MIN_ABS:
        return False
    ratio = new_count / old_count if old_count else 1
    return ratio < MIN_RATIO or ratio > MAX_RATIO


def main() -> int:
    warned = False
    for path in FILES:
        old_count = get_prev_count(path)
        new_count = get_cur_count(path)
        if old_count is None or new_count is None:
            continue
        if is_anomalous(new_count, old_count):
            print(
                "warning: rule count anomaly: %s old=%d new=%d"
                % (path, old_count, new_count)
            )
            warned = True
    if warned:
        print("warning: rule count anomalies detected, continue without blocking")
    return 0


if __name__ == "__main__":
    sys.exit(main())
