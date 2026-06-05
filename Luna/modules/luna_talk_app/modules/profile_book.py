import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional

from openai import OpenAI
from modules.chat_store import load_chat_log

JST = timezone(timedelta(hours=9))


# ============================
# 共通ユーティリティ
# ============================
def _now_iso() -> str:
    return datetime.now(JST).isoformat(timespec="seconds")


def _clip_text(s: str, max_len: int) -> str:
    s = (s or "").strip()
    if len(s) <= max_len:
        return s
    return s[: max_len - 1] + "…"


def _safe_list(xs: Any, max_items: int = 8, item_max_len: int = 24) -> List[str]:
    if not isinstance(xs, list):
        return []
    out: List[str] = []
    for x in xs:
        x = _clip_text(str(x), item_max_len)
        if x:
            out.append(x)
        if len(out) >= max_items:
            break
    return out


def _star(n: int) -> str:
    try:
        n = int(n)
    except Exception:
        n = 3
    n = max(1, min(5, n))
    return "★" * n


# ============================
# プロフィール帳 永続化
# ============================
def load_profile_book(path: Path) -> Dict[str, Any]:
    try:
        if not path.exists():
            return {}
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception as e:
        print("ProfileBook Load Error:", e)
        return {}


def save_profile_book(path: Path, book: Dict[str, Any]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(book, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("ProfileBook Save Error:", e)


# ============================
# 属性（ゲーム用・仮実装）
# ============================
def ensure_attribute(book: Dict[str, Any]) -> Dict[str, Any]:
    """
    attribute が無い場合に仮セットする。
    まずは固定で「創造」。
    """
    if not isinstance(book, dict):
        return book

    attr = str(book.get("attribute", "")).strip()
    if attr:
        return book

    book["attribute"] = "創造"
    return book


# ============================
# 履歴管理
# ============================
def _make_history_entry(book: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "updated_at": book.get("updated_at", _now_iso()),
        "title": book.get("title", ""),
        "rarity": book.get("rarity", 3),
        "delta": book.get("delta", ""),
    }


def merge_history(
    previous: Dict[str, Any],
    current: Dict[str, Any],
    keep: int = 5,
) -> Dict[str, Any]:
    prev_hist = previous.get("history", [])
    if not isinstance(prev_hist, list):
        prev_hist = []

    new_hist = [_make_history_entry(current)] + prev_hist

    seen = set()
    dedup = []
    for h in new_hist:
        if not isinstance(h, dict):
            continue
        key = (h.get("updated_at"), h.get("title"), h.get("delta"))
        if key in seen:
            continue
        seen.add(key)
        dedup.append(h)

    current["history"] = dedup[:keep]
    return current


# ============================
# AI解析：プロフィール帳生成
# ============================
def analyze_profile_book_ai(
    client: OpenAI,
    chat_log_path: Path,
    profile: Dict[str, Any],
    previous_book: Optional[Dict[str, Any]] = None,
    max_messages: int = 120,
) -> Dict[str, Any]:

    logs = load_chat_log(chat_log_path)[-max_messages:]

    call_name = profile.get("call_name", "ご主人")
    user_name = profile.get("user_name", call_name)

    lines: List[str] = []
    for m in logs:
        role = m.get("role")
        text = str(m.get("text", "")).strip()
        if not text:
            continue
        who = "USER" if role == "user" else "LUNA"
        lines.append(f"{who}: {text}")

    # ログが少ない場合
    if len(lines) < 3:
        base = {
            "updated_at": _now_iso(),
            "player_name": user_name,
            "call_name": call_name,
            "title": "はじまりの旅人",
            "rarity": 1,
            "stars": _star(1),
            "delta": "まだ記録が少ない。これから育つ。",
            "impression": "まだ記録が少ないみたい。これから一緒に育てていこう。",
            "likes": [],
            "dislikes": [],
            "habits": [],
            "strengths": ["続けようとする気持ち"],
            "support_style": "一つずつ、できた所を積み上げる",
            "recent_topics": [],
            "next_suggestions": ["会話を少しだけ増やしてみよう"],
            "luna_comment": f"{call_name}、アタイはいつでも味方だよ。",
        }

        base = ensure_attribute(base)

        if previous_book:
            base = merge_history(previous_book, base, keep=5)

        return base

    # 前回の要約（delta用）
    prev_summary = ""
    if isinstance(previous_book, dict) and previous_book:
        prev_summary = (
            "前回プロフィール帳（要約）:\n"
            f"- 称号: {previous_book.get('title','')}\n"
            f"- 属性: {previous_book.get('attribute','')}\n"
            f"- 最近: {', '.join(previous_book.get('recent_topics', [])[:5])}\n"
        )

    system_prompt = f'''
あなたは「ルナ」。{call_name}専用の相棒AIです。
目的：会話ログから、{call_name}の「プロフィール帳（ゲーム風）」を作ります。

次の形式のJSONだけを返してください：
{{
  "player_name": "プレイヤー名",
  "call_name": "{call_name}",
  "title": "称号",
  "rarity": 1,
  "delta": "前回からの変化（1行）",
  "impression": "第一印象",
  "likes": ["好き(最大8)"],
  "dislikes": ["苦手(最大8)"],
  "habits": ["口癖・行動(最大8)"],
  "strengths": ["強み(最大6)"],
  "support_style": "支え方",
  "recent_topics": ["最近の話題(最大8)"],
  "next_suggestions": ["次の行動(最大5)"],
  "luna_comment": "ルナの一言"
}}

ルール：
- rarityは1〜5
- deltaは変化点を1行で
- 断定しすぎない
- 日本語で
'''

    user_prompt = (
        "以下は会話ログです。\n"
        + (prev_summary + "\n" if prev_summary else "")
        + "\n".join(lines)
    )

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

        try:
            rarity = int(data.get("rarity", 3))
        except Exception:
            rarity = 3
        rarity = max(1, min(5, rarity))

        book: Dict[str, Any] = {
            "updated_at": _now_iso(),
            "player_name": _clip_text(data.get("player_name", user_name), 24),
            "call_name": _clip_text(data.get("call_name", call_name), 24),
            "title": _clip_text(data.get("title", "月の相棒使い"), 28),
            "rarity": rarity,
            "stars": _star(rarity),
            "delta": _clip_text(data.get("delta", "少しずつ輪郭がはっきりしてきた。"), 80),
            "impression": _clip_text(data.get("impression", ""), 140),
            "likes": _safe_list(data.get("likes")),
            "dislikes": _safe_list(data.get("dislikes")),
            "habits": _safe_list(data.get("habits")),
            "strengths": _safe_list(data.get("strengths"), max_items=6),
            "support_style": _clip_text(data.get("support_style", ""), 80),
            "recent_topics": _safe_list(data.get("recent_topics")),
            "next_suggestions": _safe_list(data.get("next_suggestions"), max_items=5, item_max_len=40),
            "luna_comment": _clip_text(data.get("luna_comment", f"{call_name}、今日もえらいよ。"), 120),
        }

        book = ensure_attribute(book)

        if previous_book:
            book = merge_history(previous_book, book, keep=5)

        return book

    except Exception as e:
        print("ProfileBook AI Error:", e)

        fallback = {
            "updated_at": _now_iso(),
            "player_name": user_name,
            "call_name": call_name,
            "title": "霧を抜ける開拓者",
            "rarity": 3,
            "stars": _star(3),
            "delta": "更新に失敗。次でリトライしよう。",
            "impression": "少し迷っても、戻ってこれる人。",
            "likes": ["AI", "制作"],
            "dislikes": ["迷いすぎ"],
            "habits": ["一つずつ進めたい"],
            "strengths": ["継続力"],
            "support_style": "小さく区切る",
            "recent_topics": ["アプリ開発"],
            "next_suggestions": ["プロフィール帳の更新"],
            "luna_comment": f"{call_name}、大丈夫だよ。",
        }

        fallback = ensure_attribute(fallback)

        if previous_book:
            fallback = merge_history(previous_book, fallback, keep=5)

        return fallback
