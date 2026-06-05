import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional

JST = timezone(timedelta(hours=9))


# ============================
# 初期値（最小＆拡張しやすい形）
# ============================
DEFAULT_PLAYER_SETTINGS: Dict[str, Any] = {
    "player_name": "ご主人",          # 表示名（ニックネーム可）
    "call_name": "ご主人",            # ルナが呼ぶ名前
    "luna_name": "ルナ",              # ルナ自身の呼称（変更可）
    "interests": [],                  # 興味（文字列リスト）
    "created_at": "",                 # ISO文字列
    "updated_at": "",                 # ISO文字列
}


def _now_iso() -> str:
    return datetime.now(JST).isoformat(timespec="seconds")


def _safe_str(x: Any, max_len: int = 40) -> str:
    s = str(x).strip()
    if not s:
        return ""
    if len(s) <= max_len:
        return s
    return s[: max_len - 1] + "…"


def _safe_list(xs: Any, max_items: int = 12, item_max_len: int = 24) -> List[str]:
    if not isinstance(xs, list):
        return []
    out: List[str] = []
    for x in xs:
        s = _safe_str(x, item_max_len)
        if s:
            out.append(s)
        if len(out) >= max_items:
            break
    # 重複除去（順序維持）
    dedup: List[str] = []
    seen = set()
    for s in out:
        if s in seen:
            continue
        seen.add(s)
        dedup.append(s)
    return dedup


def ensure_player_settings_shape(data: Any) -> Dict[str, Any]:
    """
    読み込んだJSONが古い/壊れてても落ちないように整形する
    """
    base = dict(DEFAULT_PLAYER_SETTINGS)

    if not isinstance(data, dict):
        data = {}

    base["player_name"] = _safe_str(data.get("player_name", base["player_name"]), 40) or "ご主人"
    base["call_name"] = _safe_str(data.get("call_name", base["call_name"]), 40) or "ご主人"
    base["luna_name"] = _safe_str(data.get("luna_name", base["luna_name"]), 40) or "ルナ"
    base["interests"] = _safe_list(data.get("interests", []), max_items=12, item_max_len=24)

    base["created_at"] = _safe_str(data.get("created_at", ""), 60)
    base["updated_at"] = _safe_str(data.get("updated_at", ""), 60)

    # created_at が無い場合は補う（初回ロード時にも入る）
    if not base["created_at"]:
        base["created_at"] = _now_iso()
    base["updated_at"] = _now_iso()

    return base


def load_player_settings(path: Path) -> Dict[str, Any]:
    """
    data/player_settings.json を読む。無ければデフォルトを返す。
    """
    try:
        if not path.exists():
            return ensure_player_settings_shape({})
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return ensure_player_settings_shape(data)
    except Exception as e:
        print("PlayerSettings Load Error:", e)
        return ensure_player_settings_shape({})


def save_player_settings(path: Path, settings: Dict[str, Any]) -> None:
    """
    data/player_settings.json に保存する（整形してから）
    """
    try:
        fixed = ensure_player_settings_shape(settings)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(fixed, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("PlayerSettings Save Error:", e)


def migrate_from_user_profile(user_profile: Dict[str, Any], current: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    既存の user_profile.json から player_settings に移行する補助。
    - player_name <- user_name（無ければ既存維持）
    - call_name   <- call_name
    - luna_name   <- user_calls_luna（「あなたはルナを何て呼ぶ？」の欄）
    """
    cur = ensure_player_settings_shape(current or {})
    if not isinstance(user_profile, dict):
        return cur

    # user_name はプレイヤー名に寄せる
    u_name = user_profile.get("user_name")
    if u_name:
        cur["player_name"] = _safe_str(u_name, 40) or cur["player_name"]

    c_name = user_profile.get("call_name")
    if c_name:
        cur["call_name"] = _safe_str(c_name, 40) or cur["call_name"]

    luna = user_profile.get("user_calls_luna")
    if luna:
        cur["luna_name"] = _safe_str(luna, 40) or cur["luna_name"]

    cur["updated_at"] = _now_iso()
    return cur
