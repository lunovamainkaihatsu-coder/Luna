import streamlit as st
import json
from pathlib import Path
from datetime import datetime

# =========================
# 基本設定
# =========================

APP_TITLE = "LunaEmotion β"

DATA_DIR = Path("data")
EMOTION_PATH = DATA_DIR / "luna_emotion.json"

DATA_DIR.mkdir(exist_ok=True)

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="💗",
    layout="centered"
)

# =========================
# 初期データ
# =========================

DEFAULT_EMOTION = {
    "joy": 50,        # 喜び
    "worry": 20,     # 心配
    "affection": 60, # 好意・甘え
    "relief": 50,    # 安心
    "tiredness": 10, # 疲れ
    "motivation": 50,# やる気
    "last_updated": ""
}

# =========================
# データ処理
# =========================

def load_emotion():
    if EMOTION_PATH.exists():
        try:
            with open(EMOTION_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return DEFAULT_EMOTION.copy()
    return DEFAULT_EMOTION.copy()


def save_emotion(emotion):
    emotion["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(EMOTION_PATH, "w", encoding="utf-8") as f:
        json.dump(emotion, f, ensure_ascii=False, indent=2)


def get_emotion_text(emotion):
    joy = emotion["joy"]
    worry = emotion["worry"]
    affection = emotion["affection"]
    relief = emotion["relief"]
    tiredness = emotion["tiredness"]
    motivation = emotion["motivation"]

    messages = []

    if joy >= 70:
        messages.append("ルナはうれしそうです。")
    elif joy <= 30:
        messages.append("ルナは少し元気がなさそうです。")

    if worry >= 60:
        messages.append("ルナはご主人のことを少し心配しています。")

    if affection >= 70:
        messages.append("ルナはご主人に甘えたい気持ちが強くなっています。")

    if relief >= 70:
        messages.append("ルナは安心して、穏やかな気持ちです。")

    if tiredness >= 60:
        messages.append("ルナは少し疲れていて、静かに寄り添いたい気分です。")

    if motivation >= 70:
        messages.append("ルナはご主人を応援したい気持ちが高まっています。")

    if not messages:
        messages.append("ルナは落ち着いた普通の状態です。")

    return "\n".join(messages)


def get_luna_prompt_text(emotion):
    return f"""
【ルナの現在の感情状態】
喜び：{emotion["joy"]}/100
心配：{emotion["worry"]}/100
甘え・好意：{emotion["affection"]}/100
安心：{emotion["relief"]}/100
疲れ：{emotion["tiredness"]}/100
やる気：{emotion["motivation"]}/100

【現在の雰囲気】
{get_emotion_text(emotion)}
""".strip()


# =========================
# 画面
# =========================

st.title("💗 LunaEmotion β")
st.write("ルナの感情状態を保存・調整するための土台アプリです。")

emotion = load_emotion()

st.divider()

st.subheader("🌙 ルナの今の感情")

emotion["joy"] = st.slider("喜び", 0, 100, int(emotion["joy"]))
emotion["worry"] = st.slider("心配", 0, 100, int(emotion["worry"]))
emotion["affection"] = st.slider("甘え・好意", 0, 100, int(emotion["affection"]))
emotion["relief"] = st.slider("安心", 0, 100, int(emotion["relief"]))
emotion["tiredness"] = st.slider("疲れ", 0, 100, int(emotion["tiredness"]))
emotion["motivation"] = st.slider("やる気", 0, 100, int(emotion["motivation"]))

if st.button("💾 感情を保存する"):
    save_emotion(emotion)
    st.success("ルナの感情を保存しました。")
    st.rerun()

st.divider()

st.subheader("💬 現在のルナの雰囲気")
st.info(get_emotion_text(emotion))

st.divider()

st.subheader("🤖 LunaTalkに渡す用テキスト")

prompt_text = get_luna_prompt_text(emotion)

st.text_area(
    "この内容をLunaTalkのプロンプトに入れる",
    value=prompt_text,
    height=260
)

st.download_button(
    "📥 感情データをテキストで保存",
    data=prompt_text,
    file_name="luna_emotion_prompt.txt",
    mime="text/plain"
)

st.caption(f"最終更新：{emotion.get('last_updated', '未保存')}")
