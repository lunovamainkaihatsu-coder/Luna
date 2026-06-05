import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Dict, Any


JST = timezone(timedelta(hours=9))


def _now_iso() -> str:
    return datetime.now(JST).isoformat(timespec="seconds")


def ensure_message_shape(messages: List[dict]) -> List[dict]:
    """
    message = {role: "user"|"luna", text: str, ts: str}
    古い形式でも落ちないように整形する。
    """
    fixed: List[dict] = []
    for m in messages:
        if not isinstance(m, dict):
            continue

        role = str(m.get("role", "")).strip()
        text = str(m.get("text", "")).strip()
        ts = str(m.get("ts", "")).strip() or _now_iso()

        if role not in ("user", "luna"):
            continue
        if not text:
            continue

        fixed.append({"role": role, "text": text, "ts": ts})
    return fixed


def load_chat_log(log_path: Path) -> List[dict]:
    """
    chat_log.json から読み込み。壊れてたらバックアップして空で返す。
    """
    try:
        if not log_path.exists():
            return []

        with open(log_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            return []

        return ensure_message_shape(data)

    except Exception as e:
        print("ChatLog Load Error:", e)

        # 壊れてたらバックアップ
        try:
            if log_path.exists():
                backup = log_path.with_suffix(".broken.json")
                log_path.replace(backup)
        except Exception as e2:
            print("ChatLog Backup Error:", e2)

        return []


def save_chat_log(log_path: Path, messages: List[dict]) -> None:
    """
    chat_log.json に保存
    """
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        safe = ensure_message_shape(messages)
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(safe, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("ChatLog Save Error:", e)


def append_chat_log(log_path: Path, role: str, text: str) -> None:
    """
    追記保存（安全に load -> append -> save）
    """
    role = (role or "").strip()
    text = (text or "").strip()
    if role not in ("user", "luna") or not text:
        return

    messages = load_chat_log(log_path)
    messages.append({"role": role, "text": text, "ts": _now_iso()})
    save_chat_log(log_path, messages)
