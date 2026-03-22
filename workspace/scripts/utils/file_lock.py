import json
import os
from filelock import FileLock

LOCK_DIR = os.path.expanduser("~/.openclaw_locks")
os.makedirs(LOCK_DIR, exist_ok=True)


def safe_read_json(filepath: str) -> dict:
    lock_path = os.path.join(LOCK_DIR, os.path.basename(filepath) + ".lock")
    with FileLock(lock_path, timeout=10):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)


def safe_write_json(filepath: str, data: dict) -> None:
    lock_path = os.path.join(LOCK_DIR, os.path.basename(filepath) + ".lock")
    tmp_path = filepath + ".tmp"
    with FileLock(lock_path, timeout=10):
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, filepath)


def safe_append_jsonl(filepath: str, record: dict) -> None:
    lock_path = os.path.join(LOCK_DIR, os.path.basename(filepath) + ".lock")
    with FileLock(lock_path, timeout=10):
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def safe_read_jsonl(filepath: str) -> list:
    lock_path = os.path.join(LOCK_DIR, os.path.basename(filepath) + ".lock")
    records = []
    if not os.path.exists(filepath):
        return records
    with FileLock(lock_path, timeout=10):
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    return records
