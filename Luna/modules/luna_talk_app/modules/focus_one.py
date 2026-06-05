import json
from datetime import datetime, timezone, timedelta, date
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

from openai import OpenAI

JST = timezone(timedelta(hours=9))


# ============================
# 永続化（今日の1つ）
# ============================
def _today_key() -> str:
    return date.today().isoformat()  # 例: "2026-01-29"


def load_focus_state(path: Path) -> Dict[str, Any]:
    """
    focus_one.json を読み込む。
    今日じゃないデータは返さない（今日固定）。
    """
    try:
        if not path.exists():
            return {}
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {}

        if data.get("date") != _today_key():
            return {}

        return data
    except Exception as e:
        print("FocusOne Load Error:", e)
        return {}


def save_focus_state(path: Path, state: Dict[str, Any]) -> None:
    """
    focus_one.json に保存
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("FocusOne Save Error:", e)


def clear_focus_state(path: Path) -> None:
    try:
        if path.exists():
            path.unlink()
    except Exception as e:
        print("FocusOne Clear Error:", e)


# ============================
# AIで「今日の1つ」を選ぶ
# ============================
def pick_focus_one_ai(
    client: OpenAI,
    tasks: List[dict],
    profile: Dict[str, Any],
) -> Tuple[Optional[str], str]:
    """
    未完了タスクから「今日の1つ」をAIに選ばせる。
    戻り値: (task_text or None, luna_comment)
    """
    call_name = profile.get("call_name", "ご主人")

    # 未完了だけ
    candidates = [t for t in tasks if isinstance(t, dict) and not t.get("done", False)]
    texts = [str(t.get("text", "")).strip() for t in candidates]
    texts = [x for x in texts if x]

    if not texts:
        return None, f"{call_name}、今日はタスクが空っぽみたい。まずは“1個だけ”メモしよう？"

    # 長すぎ防止（最大30件）
    texts = texts[:30]

    system_prompt = f"""
あなたは「ルナ」。{call_name}専用の相棒です。
目的：マルチタスクで迷う{call_name}のために、「今日やる1つ」だけを選びます。

必ずJSONだけを返してください：
{{
  "focus": "今日やる1つ（候補からそのまま選ぶ）",
  "comment": "ルナの一言（短く、やさしく）"
}}

ルール：
- focusは必ず候補の中から選ぶ（勝手に新規作成しない）
- 迷う人向けに“重すぎない/進めやすい”ものを優先してOK
- commentは1文でOK、責めない
"""

    user_prompt = "候補タスク一覧:\n" + "\n".join([f"- {x}" for x in texts])

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.4,
        )
        data = json.loads(resp.choices[0].message.content)

        focus = str(data.get("focus", "")).strip()
        comment = str(data.get("comment", "")).strip()

        if not focus:
            focus = texts[0]
        if not comment:
            comment = f"{call_name}、今日はこれだけで十分。いこう。"

        # 念のため候補に無い場合は先頭に落とす
        if focus not in texts:
            focus = texts[0]

        return focus, comment

    except Exception as e:
        print("FocusOne AI Error:", e)
        # フォールバック：先頭
        return texts[0], f"{call_name}、今日はまずこれを1つだけ。"


# ============================
# state組み立て
# ============================
def build_focus_state(focus_text: str, comment: str) -> Dict[str, Any]:
    return {
        "date": _today_key(),
        "updated_at": datetime.now(JST).isoformat(timespec="seconds"),
        "focus": focus_text,
        "comment": comment,
        "done": False,
    }
