#!/usr/bin/env python3
"""
file_lock.py — OpenClaw v3.11.1-Lite
并发安全的 JSON 读写工具
filelock 不可用时自动降级为无锁模式，不崩溃
"""

import json
import os
import warnings

try:
    from filelock import FileLock
    _HAS_FILELOCK = True
except ImportError:
    _HAS_FILELOCK = False
    warnings.warn(
        "⚠️  filelock 未安装，JSON 读写将使用无锁模式（并发不安全）。"
        "请执行: pip install filelock",
        RuntimeWarning,
        stacklevel=2
    )

LOCK_DIR = os.path.expanduser("~/.openclaw_locks")
os.makedirs(LOCK_DIR, exist_ok=True)


class _NoLock:
    """filelock 不可用时的空占位，保持 with 语法兼容"""
    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass


def _get_lock(filepath: str):
    if _HAS_FILELOCK:
        lock_path = os.path.join(LOCK_DIR, os.path.basename(filepath) + ".lock")
        return FileLock(lock_path, timeout=10)
    return _NoLock()


def safe_read_json(filepath: str) -> dict:
    """加锁读取 JSON 文件，返回 dict；文件不存在返回空 dict"""
    if not os.path.exists(filepath):
        return {}
    with _get_lock(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)


def safe_write_json(filepath: str, data: dict) -> None:
    """加锁写入 JSON 文件，使用临时文件保证原子性"""
    tmp_path = filepath + ".tmp"
    with _get_lock(filepath):
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, filepath)


def safe_append_jsonl(filepath: str, record: dict) -> None:
    """加锁追加一条记录到 JSONL 文件"""
    with _get_lock(filepath):
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def safe_read_jsonl(filepath: str) -> list:
    """加锁读取 JSONL 文件，返回 list；跳过无效行；文件不存在返回空 list"""
    records = []
    if not os.path.exists(filepath):
        return records
    with _get_lock(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    return records
