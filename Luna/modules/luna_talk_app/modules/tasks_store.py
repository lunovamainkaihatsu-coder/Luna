import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List
from uuid import uuid4

# JST (+09:00)
JST = timezone(timedelta(hours=9))


def _now_iso() -> str:
    return datetime.now(JST).isoformat(timespec="seconds")


def ensure_task_shape(tasks: List[dict]) -> List[dict]:
    """
    既存tasks（古い形式）を読み込んでても壊れないように整形する。
    task = {id, text, done, created_at}
    """
    fixed: List[dict] = []

    for t in tasks:
        if not isinstance(t, dict):
            continue

        tid = t.get("id") or str(uuid4())
        text = str(t.get("text", "")).strip()
        done = bool(t.get("done", False))
        created_at = t.get("created_at") or _now_iso()

        if text:
            fixed.append(
                {
                    "id": tid,
                    "text": text,
                    "done": done,
                    "created_at": created_at,
                }
            )

    return fixed


def load_tasks(tasks_path: Path) -> List[dict]:
    """
    tasks.json から読み込み。壊れてたらバックアップして空で返す。
    """
    try:
        if not tasks_path.exists():
            return []

        with open(tasks_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            return []

        return ensure_task_shape(data)

    except Exception as e:
        print("Tasks Load Error:", e)

        # 壊れてたらバックアップ（落とさない）
        try:
            if tasks_path.exists():
                backup = tasks_path.with_suffix(".broken.json")
                tasks_path.replace(backup)
        except Exception as e2:
            print("Tasks Backup Error:", e2)

        return []


def save_tasks(tasks_path: Path, tasks: List[dict]) -> None:
    """
    tasks.json に保存
    """
    try:
        tasks_path.parent.mkdir(parents=True, exist_ok=True)
        safe = ensure_task_shape(tasks)
        with open(tasks_path, "w", encoding="utf-8") as f:
            json.dump(safe, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Tasks Save Error:", e)


def add_task(tasks: List[dict], text: str) -> List[dict]:
    """
    タスク追加（返り値は新しいtasks）
    """
    text = (text or "").strip()
    if not text:
        return ensure_task_shape(tasks)

    new_task = {
        "id": str(uuid4()),
        "text": text,
        "done": False,
        "created_at": _now_iso(),
    }
    return ensure_task_shape(tasks + [new_task])


def delete_done_tasks(tasks: List[dict]) -> List[dict]:
    """
    完了タスクを削除（返り値は新しいtasks）
    """
    tasks = ensure_task_shape(tasks)
    return [t for t in tasks if not t.get("done", False)]
