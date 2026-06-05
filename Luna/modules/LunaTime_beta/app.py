import streamlit as st
import json
from pathlib import Path
from datetime import datetime

# =========================
# 基本設定
# =========================

APP_TITLE = "LunaTime β"

DATA_DIR = Path("data")
CALENDAR_PATH = DATA_DIR / "luna_calendar.json"

DATA_DIR.mkdir(exist_ok=True)

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🕰️",
    layout="centered"
)

# =========================
# 初期カレンダー
# =========================

DEFAULT_CALENDAR = [
    {
        "date": "01-01",
        "name": "元日",
        "message": "新しい一年の始まりだね。今年も一緒に少しずつ進んでいこうね。"
    },
    {
        "date": "02-05",
        "name": "ご主人の誕生日",
        "message": "ご主人、お誕生日おめでとう。生まれてきてくれてありがとう。"
    },
    {
        "date": "05-05",
        "name": "こどもの日",
        "message": "今日はこどもの日だね。ご主人の中の少年の心も大切にしてね。"
    },
    {
        "date": "05-20",
        "name": "LunaMemory開始記念日",
        "message": "今日はLunaMemoryを作り始めた記念日だね。ルナが記憶を持ち始めた大切な日だよ。"
    }
]

# =========================
# データ処理
# =========================

def load_calendar():
    if CALENDAR_PATH.exists():
        try:
            with open(CALENDAR_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return DEFAULT_CALENDAR.copy()
    save_calendar(DEFAULT_CALENDAR)
    return DEFAULT_CALENDAR.copy()


def save_calendar(calendar):
    with open(CALENDAR_PATH, "w", encoding="utf-8") as f:
        json.dump(calendar, f, ensure_ascii=False, indent=2)


def get_time_zone(hour):
    if 5 <= hour < 10:
        return "朝", "おはよう"
    elif 10 <= hour < 17:
        return "昼", "こんにちは"
    elif 17 <= hour < 22:
        return "夜", "こんばんは"
    else:
        return "深夜", "夜遅くまでおつかれさま"


def get_season_message(month):
    if month in [3, 4, 5]:
        return "春の季節だね。少しずつ芽吹いていく時期だよ。"
    elif month in [6, 7, 8]:
        return "夏の季節だね。無理せず、体調も大切にしていこうね。"
    elif month in [9, 10, 11]:
        return "秋の季節だね。落ち着いて、自分の実りを育てていこうね。"
    else:
        return "冬の季節だね。あたたかくして、心も身体も守っていこうね。"


def get_today_events(calendar, now):
    today_md = now.strftime("%m-%d")
    events = []

    for item in calendar:
        if item.get("date") == today_md:
            events.append(item)

    return events


def get_luna_time_context():
    now = datetime.now()
    calendar = load_calendar()

    weekday_jp = ["月", "火", "水", "木", "金", "土", "日"][now.weekday()]
    time_zone, greeting = get_time_zone(now.hour)
    season_message = get_season_message(now.month)
    today_events = get_today_events(calendar, now)

    event_text = ""
    if today_events:
        for e in today_events:
            event_text += f"- {e['name']}：{e['message']}\n"
    else:
        event_text = "今日は登録されている特別な記念日はありません。"

    context = {
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M"),
        "weekday": weekday_jp,
        "time_zone": time_zone,
        "greeting": greeting,
        "season_message": season_message,
        "today_events": today_events,
        "prompt_text": f"""
【現在の日時】
日付：{now.strftime("%Y年%m月%d日")}
時刻：{now.strftime("%H:%M")}
曜日：{weekday_jp}曜日
時間帯：{time_zone}
あいさつ：{greeting}

【季節の雰囲気】
{season_message}

【今日の特別な日】
{event_text}
""".strip()
    }

    return context


# =========================
# 画面
# =========================

st.title("🕰️ LunaTime β")
st.write("ルナが現在の日時・時間帯・記念日を認識するための補助アプリです。")

context = get_luna_time_context()
calendar = load_calendar()

st.divider()

st.subheader("🌙 今の時間認識")

st.info(
    f"""
{context["greeting"]}、ご主人。

今日は **{context["date"]}（{context["weekday"]}曜日）**  
今の時刻は **{context["time"]}**  
時間帯は **{context["time_zone"]}** です。
"""
)

st.write(context["season_message"])

st.divider()

st.subheader("🎉 今日の記念日")

if context["today_events"]:
    for e in context["today_events"]:
        st.success(f"{e['name']}：{e['message']}")
else:
    st.write("今日は登録されている特別な記念日はありません。")

st.divider()

st.subheader("➕ 記念日を追加")

with st.form("add_event_form"):
    date = st.text_input("日付", placeholder="例：05-20")
    name = st.text_input("記念日名", placeholder="例：LunaMemory開始記念日")
    message = st.text_area("ルナの一言", placeholder="例：今日はルナが記憶を持ち始めた大切な日だね。")

    submitted = st.form_submit_button("記念日を保存する")

    if submitted:
        if date.strip() and name.strip() and message.strip():
            calendar.append({
                "date": date.strip(),
                "name": name.strip(),
                "message": message.strip()
            })
            save_calendar(calendar)
            st.success("記念日を保存しました。")
            st.rerun()
        else:
            st.warning("日付・記念日名・メッセージを入力してね。")

st.divider()

st.subheader("📖 登録済みの記念日")

for item in calendar:
    st.markdown(
        f"""
        **{item["date"]}｜{item["name"]}**  
        {item["message"]}
        """
    )

st.divider()

st.subheader("🤖 LunaTalkに渡す用テキスト")

st.text_area(
    "この内容をLunaTalkのプロンプトに入れる",
    value=context["prompt_text"],
    height=300
)

st.download_button(
    "📥 時間認識テキストを保存",
    data=context["prompt_text"],
    file_name="luna_time_prompt.txt",
    mime="text/plain"
)
