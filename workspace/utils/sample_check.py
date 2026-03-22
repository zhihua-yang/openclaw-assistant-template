import json
import os


def is_sample_sufficient(evolution_chain_path: str, min_task_done: int = 15) -> tuple:
    """
    按有效 task-done 数量判断样本充足度，不按天数。
    返回 (sufficient: bool, count: int)
    """
    count = 0
    if not os.path.exists(evolution_chain_path):
        return False, 0
    with open(evolution_chain_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                if record.get("base_event_type") == "task-done":
                    count += 1
            except json.JSONDecodeError:
                continue
    return count >= min_task_done, count
