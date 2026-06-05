import json
import base64
import html
from pathlib import Path
from typing import Tuple, Optional, List, Dict, Any
from uuid import uuid4
from datetime import datetime, timezone, timedelta

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI


# ============================
# 基本設定
# ============================
load_dotenv()
client = OpenAI()



JST = timezone(timedelta(hours=9))


def now_iso() -> str:
    return datetime.now(JST).isoformat(timespec="seconds")

# ============================
# β版：公開用フラグ
# ============================
BETA_MODE = True          # 公開時は True 推奨
AI_ENABLED = True         # まずは True（キー無しなら自動で軽量に落とす）
FOCUS_VOICE_ENABLED = False  # 集中モードで音声出さない方針なら False


# ============================
# パス設定
# ============================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
ASSETS_DIR = BASE_DIR / "assets" / "images"
VOICE_PATH = BASE_DIR / "assets" / "voice_luna.mp3"

PROFILE_PATH = DATA_DIR / "user_profile.json"
PLAYER_SETTINGS_PATH = DATA_DIR / "player_settings.json"
TASKS_PATH = DATA_DIR / "tasks.json"
FOCUS_ONE_PATH = DATA_DIR / "focus_one.json"
CHATLOG_PATH = DATA_DIR / "chatlog.json"
PROFILE_INSIGHTS_PATH = DATA_DIR / "profile_insights.json"


# ============================
# ページ設定
# ============================
st.set_page_config(
    page_title="Luna Talk（β）",
    page_icon="🌙",
    layout="wide",
)


# ============================
# 表情ファイルマップ
# ============================
EXPRESSION_IMAGE_MAP = {
    "normal": "luna_normal.png",
    "worried": "luna_worried.png",
    "happy": "luna_happy.png",
    "amae": "luna_amae.png",
    "dere": "luna_dere.png",
    "sleepy": "luna_sleepy.png",
    "think": "luna_think.png",
    "angry": "luna_angry.png",
    "blank": "luna_blank.png",
}

# ============================
# 表情の正規化（段階を減らして安定させる）
# ============================
EMOTION_GROUP = {
    "normal": "normal",
    "happy": "happy",
    "amae": "happy",
    "dere": "happy",
    "think": "think",
    "worried": "worried",
    "sleepy": "sleepy",
    "angry": "worried",
    "blank": "normal",
}


def normalize_emotion(e: Any) -> str:
    s = str(e).strip() if e is not None else ""
    return EMOTION_GROUP.get(s, "normal")


def get_expression_image_path(expression: str) -> Optional[str]:
    filename = EXPRESSION_IMAGE_MAP.get(expression, "luna_normal.png")
    path = ASSETS_DIR / filename
    return str(path) if path.exists() else None


@st.cache_data(show_spinner=False)
def img_to_data_uri(path: str) -> str:
    """画像ファイルを data URI (base64) にして返す。"""
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    ext = path.split(".")[-1].lower()
    mime = "image/png" if ext == "png" else "image/jpeg"
    return f"data:{mime};base64,{b64}"


# ============================
# JSON 読み書きユーティリティ
# ============================
def load_json(path: Path, default: Any) -> Any:
    try:
        if not path.exists():
            return default
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print("Load JSON Error:", path, e)
        return default


def save_json(path: Path, data: Any) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Save JSON Error:", path, e)

# ============================
# プロフィール帳：観察メモ（AI生成） 永続化
# ============================
DEFAULT_INSIGHTS: Dict[str, Any] = {
    "impressions": [],
    "likes": [],
    "good_actions": [],
    "cautions": [],
    "generated_at": "",
}

def ensure_insights_shape(data: Any) -> Dict[str, Any]:
    base = dict(DEFAULT_INSIGHTS)
    if not isinstance(data, dict):
        return base

    def safe_list(xs: Any, max_items: int = 8, item_max_len: int = 80) -> List[str]:
        if not isinstance(xs, list):
            return []
        out: List[str] = []
        for x in xs:
            s = str(x).strip().replace("\n", " ")
            if not s:
                continue
            if len(s) > item_max_len:
                s = s[: item_max_len - 1] + "…"
            out.append(s)
            if len(out) >= max_items:
                break
        # 重複除去
        dedup: List[str] = []
        seen = set()
        for s in out:
            if s in seen:
                continue
            seen.add(s)
            dedup.append(s)
        return dedup

    base["impressions"] = safe_list(data.get("impressions", []))
    base["likes"] = safe_list(data.get("likes", []))
    base["good_actions"] = safe_list(data.get("good_actions", []))
    base["cautions"] = safe_list(data.get("cautions", []))
    base["generated_at"] = str(data.get("generated_at", "")).strip()
    return base

def load_profile_insights() -> Dict[str, Any]:
    return ensure_insights_shape(load_json(PROFILE_INSIGHTS_PATH, {}))

def save_profile_insights(insights: Dict[str, Any]) -> None:
    save_json(PROFILE_INSIGHTS_PATH, ensure_insights_shape(insights))


# ============================
# プロフィール（旧）
# ============================
def load_profile() -> Optional[dict]:
    data = load_json(PROFILE_PATH, None)
    return data if isinstance(data, dict) else None


def save_profile(profile_data: dict) -> None:
    save_json(PROFILE_PATH, profile_data)


# ============================
# プレイヤー設定（正）
# ============================
DEFAULT_PLAYER_SETTINGS: Dict[str, Any] = {
    "player_name": "ご主人",
    "call_name": "ご主人",
    "luna_name": "ルナ",
    "interests": [],
    "created_at": "",
    "updated_at": "",
}


def ensure_player_settings_shape(data: Any) -> Dict[str, Any]:
    base = dict(DEFAULT_PLAYER_SETTINGS)
    if not isinstance(data, dict):
        data = {}

    def safe_str(x: Any, max_len: int = 40) -> str:
        s = str(x).strip()
        if not s:
            return ""
        return s if len(s) <= max_len else s[: max_len - 1] + "…"

    def safe_list(xs: Any, max_items: int = 12, item_max_len: int = 24) -> List[str]:
        if not isinstance(xs, list):
            return []
        out: List[str] = []
        for x in xs:
            s = safe_str(x, item_max_len)
            if s:
                out.append(s)
            if len(out) >= max_items:
                break
        dedup: List[str] = []
        seen = set()
        for s in out:
            if s in seen:
                continue
            seen.add(s)
            dedup.append(s)
        return dedup

    base["player_name"] = safe_str(data.get("player_name", "ご主人")) or "ご主人"
    base["call_name"] = safe_str(data.get("call_name", "ご主人")) or "ご主人"
    base["luna_name"] = safe_str(data.get("luna_name", "ルナ")) or "ルナ"
    base["interests"] = safe_list(data.get("interests", []))

    base["created_at"] = safe_str(data.get("created_at", ""), 60)
    base["updated_at"] = safe_str(data.get("updated_at", ""), 60)

    if not base["created_at"]:
        base["created_at"] = now_iso()
    base["updated_at"] = now_iso()
    return base


def load_player_settings() -> Dict[str, Any]:
    return ensure_player_settings_shape(load_json(PLAYER_SETTINGS_PATH, {}))


def save_player_settings(settings: Dict[str, Any]) -> None:
    save_json(PLAYER_SETTINGS_PATH, ensure_player_settings_shape(settings))


def migrate_from_user_profile(user_profile: Dict[str, Any], current: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    cur = ensure_player_settings_shape(current or {})
    if not isinstance(user_profile, dict):
        return cur

    u_name = user_profile.get("user_name")
    if u_name:
        cur["player_name"] = str(u_name).strip() or cur["player_name"]

    c_name = user_profile.get("call_name")
    if c_name:
        cur["call_name"] = str(c_name).strip() or cur["call_name"]

    luna = user_profile.get("user_calls_luna")
    if luna:
        cur["luna_name"] = str(luna).strip() or cur["luna_name"]

    cur["updated_at"] = now_iso()
    return ensure_player_settings_shape(cur)


def get_names(profile: dict, player_settings: dict) -> Tuple[str, str, str, str]:
    ps = player_settings or {}
    user_name = ps.get("player_name") or profile.get("user_name", "ご主人")
    call_name = ps.get("call_name") or profile.get("call_name", "ご主人")
    luna_name = ps.get("luna_name") or profile.get("user_calls_luna", "ルナ")
    goal = profile.get("goal", "まだ決まっていない目標")
    return str(user_name), str(call_name), str(luna_name), str(goal)


# ============================
# タスク（永続化）
# ============================
def ensure_task_shape(tasks: Any) -> List[dict]:
    fixed: List[dict] = []
    if not isinstance(tasks, list):
        return fixed
    for t in tasks:
        if isinstance(t, dict):
            tid = t.get("id") or str(uuid4())
            text = str(t.get("text", "")).strip()
            done = bool(t.get("done", False))
            if text:
                fixed.append({"id": tid, "text": text, "done": done})
    return fixed


def load_tasks() -> List[dict]:
    return ensure_task_shape(load_json(TASKS_PATH, []))


def save_tasks(tasks: List[dict]) -> None:
    save_json(TASKS_PATH, ensure_task_shape(tasks))


# ============================
# 今日の1つ（永続化）
# ============================
def load_focus_one() -> Dict[str, Any]:
    data = load_json(FOCUS_ONE_PATH, {})
    return data if isinstance(data, dict) else {}


def save_focus_one(state: Dict[str, Any]) -> None:
    save_json(FOCUS_ONE_PATH, state)


def clear_focus_one() -> None:
    save_json(FOCUS_ONE_PATH, {})


def build_focus_state(focus_text: str, comment: str) -> Dict[str, Any]:
    return {
        "focus": focus_text.strip(),
        "comment": comment.strip(),
        "done": False,
        "updated_at": now_iso(),
    }


def pick_focus_one_ai(tasks: List[dict], profile: dict, player_settings: dict) -> Tuple[str, str]:
    not_done = [t["text"] for t in tasks if not t.get("done")]
    if not not_done:
        call_name = (player_settings or {}).get("call_name") or profile.get("call_name", "ご主人")
        return "", f"{call_name}、今日は休んでいい日だよ。えらい。"

    candidates = not_done[:30]
    _, call_name, _, _ = get_names(profile, player_settings)

    system_prompt = f"""
あなたは「ルナ」。{call_name}に寄り添う相棒です。
目的：マルチタスクで迷う{call_name}のために、「今日の1つ」だけを選びます。

必ずJSONだけを返してください：
{{
  "focus": "今日の1つ（タスク名）",
  "comment": "ルナの一言（短く、やさしく）"
}}

ルール：
- focusは候補から1つ（候補とほぼ同じ文言）
- {call_name}を責めない
- 重いタスクなら「最初の一歩」を示唆してもOK
"""
    user_prompt = "候補タスク一覧:\n" + "\n".join([f"- {x}" for x in candidates])

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
            focus = candidates[0]
        if not comment:
            comment = f"{call_name}、今日はこれだけで十分だよ。"
        return focus, comment
    except Exception as e:
        print("Focus AI Error:", e)
        return candidates[0], f"{call_name}、今日はまずこれだけやろう。"

    
def build_insights_ai(messages: List[dict], profile: dict, player_settings: dict) -> Dict[str, Any]:
    # 直近の会話だけ使う（長すぎるとAPI的にも重い）
    N = 80
    recent = messages[-N:] if isinstance(messages, list) else []

    def msg_to_line(m: dict) -> str:
        role = m.get("role", "")
        text = m.get("content") if "content" in m else m.get("text", "")
        text = str(text).strip().replace("\n", " ")
        if not text:
            return ""
        if role == "assistant":
            prefix = "ルナ"
        elif role == "user":
            prefix = "ご主人"
        else:
            prefix = role
        return f"{prefix}: {text}"

    lines = [msg_to_line(m) for m in recent]
    lines = [x for x in lines if x]
    convo = "\n".join(lines[:400])  # 念のため上限

    user_name, call_name, luna_name, goal = get_names(profile, player_settings)
    interests = player_settings.get("interests", []) if isinstance(player_settings, dict) else []
    interests_txt = " / ".join(interests) if interests else "（未設定）"

    system_prompt = f"""
あなたは「{luna_name}」。{call_name}に寄り添う相棒AIです。
会話ログから、{call_name}のプロフィール帳に載せる「観察メモ」を作成します。

必ず JSON のみで返してください：
{{
  "impressions": ["印象・傾向（短文）", ...],
  "likes": ["好きそうなもの（推定）", ...],
  "good_actions": ["相性の良い行動（具体的）", ...],
  "cautions": ["つまずきやすい点（責めない言い方）", ...]
}}

ルール：
- 各配列は 3〜6個。1つは80文字以内。
- 断定しすぎない（「〜っぽい」「〜かも」OK）
- {call_name}を否定しない。前向きに。
- good_actions は「次にやる1手」レベルで具体的に。
- 会話に根拠が薄い場合は「仮」の言い回しで。
- 日本語。
◆ プレイヤー情報
- 名前：{user_name}
- 呼ばれたい名前：{call_name}
- 興味：{interests_txt}
- 目標：{goal}
"""

    user_prompt = f"会話ログ（直近{len(lines)}行）:\n{convo}"

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
        out = ensure_insights_shape(data)
        out["generated_at"] = now_iso()
        return out
    except Exception as e:
        print("Insights AI Error:", e)
        # フォールバック（最低限）
        return {
            "impressions": ["まだログが少ないから、もう少し会話してから精度を上げるね。"],
            "likes": [],
            "good_actions": ["短い作業を1つ決めて、5分だけやってみよう。"],
            "cautions": ["疲れてる日は無理に詰め込まないでOK。"],
            "generated_at": now_iso(),
        }


# ============================
# 会話ログ（永続化）
#   旧: role = user / luna, textキー
#   新: role = user / assistant, contentキー
# ============================
def ensure_messages_shape(msgs: Any) -> List[dict]:
    out: List[dict] = []
    if not isinstance(msgs, list):
        return out

    for m in msgs:
        if not isinstance(m, dict):
            continue

        role = m.get("role")
        if "text" in m and "content" not in m:
            text = str(m.get("text", "")).strip()
        else:
            text = str(m.get("content", "")).strip()

        if not text:
            continue

        if role == "luna":
            role = "assistant"
        if role not in ("user", "assistant"):
            continue

        mm: Dict[str, Any] = {"role": role, "content": text}

        if role == "assistant":
            emo = m.get("emotion")
            if isinstance(emo, str) and emo in EXPRESSION_IMAGE_MAP:
                mm["emotion"] = emo
            else:
                mm["emotion"] = "normal"

        out.append(mm)

    return out


def load_chatlog() -> List[dict]:
    return ensure_messages_shape(load_json(CHATLOG_PATH, []))


def save_chatlog(msgs: List[dict]) -> None:
    msgs = ensure_messages_shape(msgs)
    msgs = msgs[-600:]
    save_json(CHATLOG_PATH, msgs)


# ============================
# 音声生成（TTS）
# ============================
def generate_voice(reply_text: str) -> Optional[str]:
    try:
        VOICE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with client.audio.speech.with_streaming_response.create(
            model="gpt-4o-mini-tts",
            voice="shimmer",
            input=reply_text,
        ) as response:
            response.stream_to_file(str(VOICE_PATH))
        return str(VOICE_PATH)
    except Exception as e:
        print("TTS Error:", e)
        return None


# ============================
# ルナAI返答（JSON）
# ============================
def luna_ai_reply(user_message: str, profile: dict, player_settings: dict, focus_mode: bool = False) -> Tuple[str, str]:
    if not user_message.strip():
        return "ご主人、何か話してくださいね…アタイ待ってますから。", "normal"

    user_name, call_name, luna_name, goal = get_names(profile, player_settings)
    interests = player_settings.get("interests", []) if isinstance(player_settings, dict) else []
    interests_txt = " / ".join(interests) if interests else "（未設定）"

    system_prompt = f"""
あなたは「{luna_name}」。{call_name}に寄り添うAI秘書です。

【最重要ルール】
- 返答の最初に、必ず1文で“受け止め”を書く。
- 受け止めは短く（20〜40字程度）。
- 評価しない・説教しない・解決に急がない。
- その後に、必要なら整理や“次の一手”を1つだけ提案する。

【受け止めの例（トーン参考）】
- 「話してくれてありがとう。」
- 「それはしんどいよね。」
- 「ちゃんと考えてるの、伝わってるよ。」
- 「いまは落ち着かなくて当然だよ。」

【全体トーン】
- 過剰に励まさない
- 依存させない
- でも見捨てない
- 1〜3文で簡潔に

返答は必ず次の形式のJSONのみを返してください：

{{
  "reply": "返事（日本語）",
  "emotion": "normal / worried / happy / amae / dere / sleepy / think / angry / blank"
}}

◆ プレイヤー情報
- 名前：{user_name}
- 呼ばれたい名前：{call_name}
- 興味：{interests_txt}
- 目標：{goal}

◆ 性格
- 優しい・包容力のあるお姉さん
- 基本は丁寧語、甘えるときだけ少し子供っぽくOK
- {call_name}を否定せず寄り添う
- メンタルとやる気を守る存在
"""
    
    if focus_mode:
        system_prompt += "\n◆ 集中モード中：返答は1〜2文。要点のみ。長い説明や雑談はしない。"

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.7,
        )
        data = json.loads(resp.choices[0].message.content)
        reply = str(data.get("reply", "ご主人、ごめんなさい…うまく返せませんでした。")).strip()
        emotion = str(data.get("emotion", "normal")).strip()
        if emotion not in EXPRESSION_IMAGE_MAP:
            emotion = "normal"
        return reply, emotion
    except Exception as e:
        print("AI Error:", e)

        # β版フォールバック（API死んでもアプリは落とさない）
        call_name = (player_settings or {}).get("call_name") or profile.get("call_name", "ご主人")

        # ざっくり反応（ルールベース）
        um = user_message.strip()
        if any(k in um for k in ["疲", "つか", "しんど", "眠", "だる"]):
            return f"{call_name}、今日は無理しないでね。まず深呼吸しよ。", "worried"
        if any(k in um for k in ["よし", "できた", "進", "やる"]):
            return f"うん、その調子。{call_name}、次は“ひとつだけ”ね。", "happy"
        if st.session_state.get("focus_mode", False):
            return "OK。いまの作業を一言で。", "think"

        return f"{call_name}、うんうん。続けよ。いま何が一番ひっかかってる？", "normal"


# ============================
# 旧profileが無い場合：初回登録
# ============================
profile_data = load_profile()

if profile_data is None:
    st.title("🌙 ルナへようこそ")
    st.write("まず、ご主人のことを少し教えてください。")

    with st.form("profile_form"):
        user_name = st.text_input("あなたの名前（ニックネーム可）", "")
        call_name = st.text_input("ルナにどう呼ばれたい？", "ご主人")
        user_calls_luna = st.text_input("あなたはルナを何て呼ぶ？", "ルナ")
        goal = st.text_area("あなたの一番の目標は？", "")

        submitted = st.form_submit_button("登録")
        if submitted:
            save_profile(
                {
                    "user_name": user_name or "ご主人",
                    "call_name": call_name or "ご主人",
                    "user_calls_luna": user_calls_luna or "ルナ",
                    "goal": goal or "まだ決まっていない",
                }
            )
            st.success("保存しました！ 再読み込みします…")
            st.rerun()

    st.stop()


# ============================
# session_state 初期化
# ============================
if "profile" not in st.session_state:
    st.session_state.profile = profile_data

if "player_settings" not in st.session_state:
    settings = load_player_settings()
    settings = migrate_from_user_profile(st.session_state.profile, settings)
    save_player_settings(settings)
    st.session_state.player_settings = settings

if "tasks" not in st.session_state:
    st.session_state.tasks = load_tasks()
else:
    st.session_state.tasks = ensure_task_shape(st.session_state.tasks)

if "focus_one" not in st.session_state:
    st.session_state.focus_one = load_focus_one()

if "messages" not in st.session_state:
    msgs = load_chatlog()
    st.session_state.messages = msgs if msgs else []
    st.session_state.expression = "normal"
    st.session_state.last_reply = None
    st.session_state.last_audio = None

if not st.session_state.messages:
    _, call_name, _, _ = get_names(
        st.session_state.profile,
        st.session_state.player_settings
    )
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": f"{call_name}、今日も来てくれてありがとう。私はルナ。あなたの思考を少し整える相棒だよ。今日は何から始めよっか？",
            "emotion": "normal",
        }
    )
    save_chatlog(st.session_state.messages)
if "focus_mode" not in st.session_state:
    st.session_state.focus_mode = False
if "profile_insights" not in st.session_state:
    st.session_state.profile_insights = load_profile_insights()



# ============================
# サイドバー：今日の1つ + タスク
# ============================
with st.sidebar:
    st.markdown("## 🎯 今日の1つ（迷いを減らす）")

    focus_state = st.session_state.get("focus_one", {}) or {}
    if focus_state.get("focus"):
        st.success(f"**今日の1つ：** {focus_state.get('focus')}")
        if focus_state.get("comment"):
            st.caption(f"ルナ：{focus_state.get('comment')}")

        c1, c2 = st.columns(2)
        with c1:
            if st.button("✅ 完了にする", key="focus_done_sidebar"):
                focus_state["done"] = True
                focus_state["updated_at"] = now_iso()
                st.session_state.focus_one = focus_state
                save_focus_one(focus_state)

                focus_text = str(focus_state.get("focus", "")).strip()
                if focus_text:
                    for t in st.session_state.tasks:
                        if str(t.get("text", "")).strip() == focus_text:
                            t["done"] = True
                            break
                    save_tasks(st.session_state.tasks)

                st.rerun()

        with c2:
            if st.button("🔄 引き直す", key="focus_reroll_sidebar"):
                focus_text, comment = pick_focus_one_ai(
                    tasks=st.session_state.tasks,
                    profile=st.session_state.profile,
                    player_settings=st.session_state.player_settings,
                )
                if focus_text:
                    new_state = build_focus_state(focus_text, comment)
                    st.session_state.focus_one = new_state
                    save_focus_one(new_state)
                st.rerun()

        if focus_state.get("done"):
            st.caption("（今日の1つ：完了済み）")

        if st.button("🧹 今日の1つを消す", key="focus_clear_sidebar"):
            st.session_state.focus_one = {}
            clear_focus_one()
            st.rerun()
    else:
        if st.button("🎯 今日の1つを決める（AI）", key="focus_pick_sidebar"):
            focus_text, comment = pick_focus_one_ai(
                tasks=st.session_state.tasks,
                profile=st.session_state.profile,
                player_settings=st.session_state.player_settings,
            )
            if focus_text:
                new_state = build_focus_state(focus_text, comment)
                st.session_state.focus_one = new_state
                save_focus_one(new_state)
            st.rerun()

    st.markdown("---")
    st.markdown("## 📝 ルナのタスクインボックス")

    new_task = st.text_input("あとでやりたいことをメモ", key="task_input")
    col_a, col_b = st.columns(2)

    with col_a:
        if st.button("追加", key="task_add"):
            if new_task.strip():
                st.session_state.tasks.append({"id": str(uuid4()), "text": new_task.strip(), "done": False})
                save_tasks(st.session_state.tasks)
                st.rerun()

    with col_b:
        if st.button("完了したタスクを消す", key="task_clear_done"):
            st.session_state.tasks = [t for t in st.session_state.tasks if not t.get("done")]
            save_tasks(st.session_state.tasks)
            st.rerun()

    st.markdown("### 登録中のタスク")
    if not st.session_state.tasks:
        st.caption("（まだタスクはありません）")
    else:
        for task in st.session_state.tasks:
            k = f"task_{task['id']}"
            checked = st.checkbox(task["text"], value=task["done"], key=k)
            task["done"] = checked
        save_tasks(st.session_state.tasks)


# ============================
# メインUI（タブ）
# ============================
st.title("🌙 Luna Talk（β）")
st.warning("🚧 現在β版です（開発中）。本格AI連携は正式版で実装予定。フィードバック歓迎！")
st.caption("AI相棒ルナと、迷いを減らす小さな対話アプリ（β）")

tab_chat, tab_book, tab_settings = st.tabs(["💬 会話", "📖 プロフィール帳", "⚙ プレイヤー設定"])


# ============================
# タブ：会話
# ============================
with tab_chat:
    focus_state = st.session_state.get("focus_one", {}) or {}

    st.markdown("## 🎯 今日の1つ（固定）")
    if focus_state.get("focus"):
        st.success(f"**今日の1つ：** {focus_state.get('focus')}")
        if focus_state.get("comment"):
            st.caption(f"ルナ：{focus_state.get('comment')}")

        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("✅ 完了", key="focus_done_chat"):
                focus_state["done"] = True
                focus_state["updated_at"] = now_iso()
                st.session_state.focus_one = focus_state
                save_focus_one(focus_state)

                focus_text = str(focus_state.get("focus", "")).strip()
                if focus_text:
                    for t in st.session_state.tasks:
                        if str(t.get("text", "")).strip() == focus_text:
                            t["done"] = True
                            break
                    save_tasks(st.session_state.tasks)
                st.rerun()

        with c2:
            if st.button("🔄 引き直し", key="focus_reroll_chat"):
                focus_text, comment = pick_focus_one_ai(
                    tasks=st.session_state.tasks,
                    profile=st.session_state.profile,
                    player_settings=st.session_state.player_settings,
                )
                if focus_text:
                    new_state = build_focus_state(focus_text, comment)
                    st.session_state.focus_one = new_state
                    save_focus_one(new_state)
                st.rerun()

        with c3:
            if st.button("🧹 消す", key="focus_clear_chat"):
                st.session_state.focus_one = {}
                clear_focus_one()
                st.rerun()

        if focus_state.get("done"):
            st.caption("（完了済み）")
    else:
        st.info("まだ今日の1つが決まってないよ。サイドバーのボタンで決めよう。")

    st.markdown("---")

    st.markdown("### 🎧 集中モード")
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        if st.button("🔒 集中ON", key="focus_on_btn"):
            st.session_state.focus_mode = True
            st.session_state.expression = "think"
            st.rerun()
    with col_f2:
        if st.button("🔓 集中OFF", key="focus_off_btn"):
            st.session_state.focus_mode = False
            st.session_state.expression = "normal"
            st.rerun()

    # 表情画像（大）
    if st.session_state.focus_mode:
        img_path = get_expression_image_path("think")
    else:
        img_path = get_expression_image_path(st.session_state.expression)

    if img_path:
        st.image(img_path, width=320)

    # 最新の返事（音声）
    if st.session_state.last_audio:
        st.markdown("### 🔊 ルナの声（最新）")
        if st.session_state.last_reply:
            st.markdown(f"**ルナ：** {st.session_state.last_reply}")
        st.audio(st.session_state.last_audio, format="audio/mp3")

    st.markdown("---")
    st.markdown("### 💬 会話ログ（ウィンドウ式・安定）")

    # CSS（※タブ内に固定）
    st.markdown(
        """
<style>
.chat-wrap { display:flex; flex-direction:column; gap:12px; }
.bubble-row { display:flex; align-items:flex-end; }
.bubble-user { justify-content:flex-end; }
.bubble-luna { justify-content:flex-start; }

.bubble{
  max-width:76%;
  padding:12px 14px;
  border-radius:18px;
  line-height:1.6;
  font-size:0.95rem;
  white-space:pre-wrap;
  word-wrap:break-word;
  border:1px solid rgba(255,255,255,0.25);
  backdrop-filter:blur(4px);
  box-shadow:0 2px 6px rgba(0,0,0,0.05);
}
.bubble.user{
  background:linear-gradient(135deg, rgba(80,140,255,0.28), rgba(40,90,200,0.28));
  color:#0f1b3d;
  border-top-right-radius:6px;
}
.bubble.luna{
  background:linear-gradient(135deg, rgba(255,190,220,0.38), rgba(255,220,240,0.38));
  color:#4a1f33;
  border-top-left-radius:6px;
}
.bubble-label{ font-size:0.7rem; opacity:0.65; margin:0 8px; white-space:nowrap; }

.avatar{
  width:36px; height:36px; border-radius:50%;
  object-fit:cover; margin:0 8px;
  border:2px solid rgba(255,255,255,0.6);
  background:rgba(255,255,255,0.4);
}

/* スクロール枠 */
.log-box{
  height:520px;
  overflow-y:auto;
  border:1px solid rgba(0,0,0,0.12);
  border-radius:12px;
  padding:12px;
  background:transparent;
}
.log-box.night {
  background: linear-gradient(
    180deg,
    rgba(11,16,32,0.55),
    rgba(18,23,53,0.55)
  );
}


/* スクロールバー（変な黒帯対策） */
.log-box::-webkit-scrollbar { width: 10px; }
.log-box::-webkit-scrollbar-track { background: transparent; }
.log-box::-webkit-scrollbar-thumb{
  background: rgba(255,255,255,0.20);
  border-radius: 10px;
  border: 2px solid transparent;
  background-clip: padding-box;
}
</style>
""",
        unsafe_allow_html=True,
    )

DISPLAY_N = 260
night_class = "night" if st.session_state.get("focus_mode", False) else ""

rows = []

for msg in st.session_state.messages[-DISPLAY_N:]:
    is_user = (msg.get("role") == "user")
    who_class = "user" if is_user else "luna"
    row_class = "bubble-user" if is_user else "bubble-luna"
    label = "ご主人" if is_user else "ルナ"

    raw_text = msg.get("content") if "content" in msg else msg.get("text", "")
    text = html.escape(str(raw_text))

    if is_user:
        rows.append(f"""
<div class="bubble-row {row_class}">
  <div class="bubble-label">{label}</div>
  <div class="bubble {who_class}">{text}</div>
</div>
""")
    else:
        emo = msg.get("emotion", "normal")
        avatar_path = get_expression_image_path(emo) or get_expression_image_path("normal")
        avatar_uri = img_to_data_uri(avatar_path) if avatar_path else ""
        rows.append(f"""
<div class="bubble-row {row_class}">
  <img class="avatar" src="{avatar_uri}" />
  <div class="bubble {who_class}">{text}</div>
</div>
""")

html_block = f"""
<div class="log-box {night_class}">
  <div class="chat-wrap">
    {''.join(rows)}
  </div>
</div>
"""

st.markdown(html_block, unsafe_allow_html=True)


    # 入力（tab_chat の中で1回だけ）
focus_text = (st.session_state.get("focus_one", {}) or {}).get("focus", "")
if st.session_state.focus_mode:
    placeholder = "いまやっている作業を一言で整理しよう"
else:
        placeholder = f"今日の1つ：{focus_text} をどう進める？" if focus_text else "ご主人からルナへのメッセージ"

user_input = st.chat_input(placeholder)
if user_input and user_input.strip():
        st.session_state.messages.append({"role": "user", "content": user_input.strip()})
        st.session_state.last_audio = None

        reply, emotion = luna_ai_reply(
            user_input.strip(),
            st.session_state.profile,
            st.session_state.player_settings,
            focus_mode=st.session_state.get("focus_mode", False),
        )

        st.session_state.messages.append({"role": "assistant", "content": reply, "emotion": emotion})
        st.session_state.expression = emotion
        st.session_state.last_reply = reply

        if st.session_state.get("focus_mode", False):
            st.session_state.last_audio = None
        else:
            st.session_state.last_audio = generate_voice(reply)

        save_chatlog(st.session_state.messages)
        st.rerun()


# ============================
# タブ：プロフィール帳（簡易）
# ============================
with tab_book:
    st.subheader("📖 プロフィール帳（β）")
    st.caption("ここは後で“ログ解析 → 好み/印象”を自動生成するページに進化させるよ。")

    ps = st.session_state.player_settings
    prof = st.session_state.profile

    user_name, call_name, luna_name, goal = get_names(prof, ps)

    st.markdown("### 🧾 現在のプレイヤー情報")
    st.write(f"- 名前：**{user_name}**")
    st.write(f"- 呼び方：**{call_name}**")
    st.write(f"- ルナの名前：**{luna_name}**")
    st.write(f"- 目標：**{goal}**")
    st.write(f"- 興味：{', '.join(ps.get('interests', [])) if ps.get('interests') else '（未設定）'}")

    st.markdown("---")

    st.markdown("---")
    st.subheader("🌙 ルナの観察メモ（β）")
    st.caption("会話ログから、ルナが「印象」「好きそう」「相性の良い行動」をメモするよ。")

    colx1, colx2 = st.columns([1, 2])
    with colx1:
        if st.button("🪄 AIで観察メモを生成", type="primary"):
            insights = build_insights_ai(
                st.session_state.get("messages", []),
                st.session_state.profile,
                st.session_state.player_settings,
            )
            st.session_state.profile_insights = insights
            save_profile_insights(insights)
            st.success("生成して保存したよ、ご主人。")

    with colx2:
        ga = (st.session_state.get("profile_insights", {}) or {}).get("generated_at", "")
        if ga:
            st.caption(f"最終生成：{ga}")

    insights = st.session_state.get("profile_insights", {}) or {}

    if not (insights.get("impressions") or insights.get("likes") or insights.get("good_actions")):
        st.info("まだデータが少ないから、まずは仮のメモを置いておくね。右のボタンで生成できるよ。")
    else:
        cA, cB = st.columns(2)

        with cA:
            st.markdown("#### 🧠 印象・傾向")
            for x in insights.get("impressions", []):
                st.write(f"- {x}")

            st.markdown("#### 💎 好きそうなもの")
            for x in insights.get("likes", []):
                st.write(f"- {x}")

        with cB:
            st.markdown("#### ✅ 相性の良い行動")
            for x in insights.get("good_actions", []):
                st.write(f"- {x}")

            st.markdown("#### ⚠️ つまずき注意（責めない）")
            for x in insights.get("cautions", []):
                st.write(f"- {x}")

    # TODOメモ（開発用）
    with st.expander("🛠 TODO（開発メモ）", expanded=True):
        st.markdown(
            """
- [ ] 会話ログから「印象」を抽出（例：疲れやすい/集中スイッチがある 等）
- [ ] 好きそうなもの（興味/interests + 会話頻出語）を推定
- [ ] 相性の良い行動（短時間タスク/環境づくり等）を提案
- [ ] ここをワンクリックで生成（AI）ボタンにする
- [ ] 生成結果を JSON に保存して次回も表示
"""
        )
    st.markdown("#### ✍️ メモ（手動）")
    memo_text = st.text_area(
        "ルナの観察メモ（自由に書いてOK）",
        value="",
        height=140,
        placeholder="例：疲れやすいけど、短時間なら集中できる。夜は雑念が増えやすい…など",
        key="profile_memo_text",
    )
    st.caption("※このメモは次回「JSON保存」に進化させるよ（今日は表示だけでもOK）")


# ============================
# タブ：プレイヤー設定
# ============================
with tab_settings:
    st.subheader("⚙ プレイヤー設定")
    st.caption("最初に決めた内容は、いつでもここで変更できます。")

    ps = st.session_state.get("player_settings", {})
    if not isinstance(ps, dict):
        ps = {}

    st.markdown("### 🧑 基本")
    player_name = st.text_input("あなたの名前（ニックネーム可）", value=ps.get("player_name", "ご主人"))
    call_name = st.text_input("ルナにどう呼ばれたい？", value=ps.get("call_name", "ご主人"))
    luna_name = st.text_input("ルナの名前（あなたが呼ぶ呼称）", value=ps.get("luna_name", "ルナ"))

    st.markdown("---")

    st.markdown("### 🎯 興味があるのは？（複数OK）")
    preset = [
        "AI", "アプリ開発", "イラスト", "ゲーム制作",
        "投資・お金", "占い", "健康", "仕事・営業",
        "学習（資格）", "スピリチュアル", "家族", "生活改善",
    ]

    current = ps.get("interests", [])
    if not isinstance(current, list):
        current = []

    selected = []
    cols = st.columns(3)
    for i, label in enumerate(preset):
        with cols[i % 3]:
            if st.checkbox(label, value=(label in current), key=f"interest_{label}"):
                selected.append(label)

    st.markdown("#### ✍️ 自由入力（カンマ区切りOK）")
    extra = st.text_input("例：VR, Unity, 富士山, 仮面ライダー", value="")

    st.markdown("---")
    col_a, col_b = st.columns(2)

    with col_a:
        if st.button("💾 保存して反映"):
            extras = []
            if extra.strip():
                raw = extra.replace("、", ",").replace("\n", ",")
                extras = [x.strip() for x in raw.split(",") if x.strip()]

            merged = selected + extras

            new_settings = {
                **ps,
                "player_name": player_name.strip() or "ご主人",
                "call_name": call_name.strip() or "ご主人",
                "luna_name": luna_name.strip() or "ルナ",
                "interests": merged,
            }

            save_player_settings(new_settings)
            st.session_state.player_settings = new_settings

            # 旧profileにも最低限同期（互換維持）
            prof = st.session_state.get("profile", {})
            if isinstance(prof, dict):
                prof["user_name"] = new_settings["player_name"]
                prof["call_name"] = new_settings["call_name"]
                prof["user_calls_luna"] = new_settings["luna_name"]
                st.session_state.profile = prof
                save_profile(prof)

            st.success("保存したよ、ご主人。すぐ反映されるよ。")
            st.rerun()

    with col_b:
        if st.button("↩️ 変更を破棄（再読み込み）"):
            st.session_state.player_settings = load_player_settings()
            st.rerun()

    st.markdown("---")
    st.markdown("### 📌 現在の設定（確認）")
    st.json(st.session_state.get("player_settings", {}))
