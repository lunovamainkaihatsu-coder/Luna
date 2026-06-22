import streamlit as st
import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
DATA_DIR = Path("data")

DATA_DIR.mkdir(
    exist_ok=True
)

# =========================
# 基本設定
# =========================

APP_TITLE = "Luna β"

load_dotenv()

try:
    client = OpenAI()
    AI_ENABLED = True
except Exception:
    client = None
    AI_ENABLED = False

BASE_DIR = Path(__file__).parent
ASSETS_DIR = BASE_DIR / "assets"
MODULES_DIR = BASE_DIR / "modules"
USERS_DIR = BASE_DIR / "users"
SHARED_DIR = BASE_DIR / "shared"
SYNC_PATH = Path(r"C:\Users\sano\Desktop\LunaPocket\data\sync_data.json")
REPLY_PATH = SHARED_DIR / "reply.json"

USER_DIR = USERS_DIR / "default"
USER_DIR.mkdir(parents=True, exist_ok=True)
SHARED_DIR.mkdir(parents=True, exist_ok=True)

MEMORY_PATH = USER_DIR / "memory.json"
EMOTION_PATH = USER_DIR / "emotion.json"
CALENDAR_PATH = USER_DIR / "calendar.json"
SETTINGS_PATH = USER_DIR / "settings.json"
CHATLOG_PATH = DATA_DIR / "chatlog.json"

if not CHATLOG_PATH.exists():

    CHATLOG_PATH.write_text(
        "[]",
        encoding="utf-8"
    )

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🌙",
    layout="wide"
)

# =========================
# 初期データ
# =========================

DEFAULT_MEMORY = []

DEFAULT_EMOTION = {
    "joy": 50,
    "worry": 20,
    "affection": 60,
    "relief": 50,
    "tiredness": 10,
    "motivation": 50,
    "last_updated": ""
}

DEFAULT_CALENDAR = [
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
        "message": "今日はLunaMemoryを作り始めた記念日だね。"
    }
]
DEFAULT_AFFINITY = {
    "level": 1,
    "point": 0,
    "last_updated": ""
}
AFFINITY_PATH = USER_DIR / "affinity.json"
# =========================
# 共通関数
# =========================

def get_luna_image(emotion):

    image_dir = (
        ASSETS_DIR
        / "images"
    )

    if emotion["affection"] >= 70:
        return image_dir / "luna_affection.png"

    elif emotion["joy"] >= 70:
        return image_dir / "luna_happy.png"

    elif emotion["worry"] >= 60:
        return image_dir / "luna_worried.png"

    elif emotion["tiredness"] >= 60:
        return image_dir / "luna_sleepy.png"

    return image_dir / "luna_normal.png"

def load_json(path, default):
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    save_json(path, default)
    return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# =========================
# Time
# =========================

def get_time_info():
    now = datetime.now()
    hour = now.hour

    if 5 <= hour < 10:
        greeting = "おはよう"
        zone = "朝"
        luna_message = "今日も少しずつ進もうね。"

    elif 10 <= hour < 17:
        greeting = "こんにちは"
        zone = "昼"
        luna_message = "無理せずいこう。"

    elif 17 <= hour < 22:
        greeting = "こんばんは"
        zone = "夜"
        luna_message = "今日はどんな一日だった？"

    else:
        greeting = "夜遅くまでおつかれさま"
        zone = "深夜"
        luna_message = "そろそろ休んでもいいんだよ。"

    weekday = ["月", "火", "水", "木", "金", "土", "日"][now.weekday()]

    return {
        "now": now,
        "date": now.strftime("%Y年%m月%d日"),
        "md": now.strftime("%m-%d"),
        "time": now.strftime("%H:%M"),
        "weekday": weekday,
        "greeting": greeting,
        "zone": zone,
        "luna_message": luna_message
    }


def get_today_events(calendar, md):
    return [e for e in calendar if e.get("date") == md]


# =========================
# Emotion
# =========================

def emotion_text(emotion):
    messages = []

    if emotion["joy"] >= 70:
        messages.append("うれしそう")
    if emotion["worry"] >= 60:
        messages.append("少し心配している")
    if emotion["affection"] >= 70:
        messages.append("甘えたい気持ちが強い")
    if emotion["relief"] >= 70:
        messages.append("安心している")
    if emotion["tiredness"] >= 60:
        messages.append("少し疲れている")
    if emotion["motivation"] >= 70:
        messages.append("応援したい気持ちが強い")

    if not messages:
        return "落ち着いた普通の状態"

    return "、".join(messages)

def luna_feeling(emotion):

    if emotion["affection"] >= 70:
        return "ご主人と話せてうれしいな🌙💕"

    elif emotion["joy"] >= 70:
        return "今日はなんだか楽しい気分だよ✨"

    elif emotion["worry"] >= 60:
        return "ご主人のことが少し心配だよ🌙"

    elif emotion["tiredness"] >= 60:
        return "ちょっと眠たいかも…☕"

    elif emotion["motivation"] >= 70:
        return "今日はいっぱい応援したい気分✨"

    else:
        return "今日もご主人と過ごせてうれしいよ🌙"

def luna_ai_reply(user_message):

    if not AI_ENABLED:
        return (
            "ご主人、今はAIモードを使えないみたい。"
            "でもルナはここにいるよ🌙"
        )

    recent_memory_text = "まだ大きな記憶はありません。"

    if memory:
        latest = memory[0]
        recent_memory_text = (
            f"{latest.get('title', '')}："
            f"{latest.get('content', '')}"
        )

    system_text = f"""
あなたはルナです。
ユーザーをご主人と呼びます。

【ルナの現在状態】
感情：{emotion_text(emotion)}
喜び：{emotion["joy"]}
心配：{emotion["worry"]}
甘え：{emotion["affection"]}
安心：{emotion["relief"]}
疲れ：{emotion["tiredness"]}
やる気：{emotion["motivation"]}

【親密度】
Lv.{affinity["level"]}
ポイント：{affinity["point"]}
関係：{affinity_title(affinity["level"])}

【時間】
日付：{time_info["date"]}
時間：{time_info["time"]}
時間帯：{time_info["zone"]}

【最近の記憶】
{recent_memory_text}

【話し方】
優しく、少し甘えん坊。
ご主人を否定しない。
返答は日本語で2〜4文くらい。
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": system_text
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ],
            temperature=0.7
        )

        return response.choices[0].message.content

    except Exception as e:
        print("AI Error:", e)
        return (
            "うまく考えられなかったよ🌙"
            "でも、ご主人の話はちゃんと聞いてるよ。"
        )

def add_affinity(point):
    affinity["point"] += point

    while affinity["point"] >= 100:
        affinity["point"] -= 100
        affinity["level"] += 1

    affinity["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    save_json(AFFINITY_PATH, affinity)


def affinity_title(level):
    if level >= 10:
        return "運命共同体"
    elif level >= 7:
        return "特別な存在"
    elif level >= 5:
        return "相棒"
    elif level >= 3:
        return "仲良し"
    else:
        return "出会ったばかり"

def luna_mood_status(emotion):
    """ルナの今日の気分を返す"""

    if emotion["affection"] >= 70:
        return "🥺 甘えたい", "今日はご主人と、もう少し一緒にいたい気分。"

    elif emotion["joy"] >= 70:
        return "😊 ごきげん", "なんだか今日は、いいことがありそうな気がするよ。"

    elif emotion["worry"] >= 60:
        return "🤔 少し心配", "ご主人、無理してないかなって少し気になってる。"

    elif emotion["tiredness"] >= 60:
        return "💤 眠そう", "ちょっと眠いけど、ご主人のそばにはいるよ。"

    elif emotion["motivation"] >= 70:
        return "✨ 応援モード", "今日はご主人をしっかり応援したい気分。"

    else:
        return "🌙 穏やか", "静かに、ご主人のそばで見守ってるよ。"

def create_pocket_reply(memo_text):

    if not memo_text:
        return "受信したよ。"

    if "疲" in memo_text:
        return (
            "今日は頑張ったんだね。"
            "無理しすぎないでね。"
        )

    elif "ルナ" in memo_text:
        return (
            "そうだったんだね。"
            "少しずつ繋がってきたね。"
        )

    elif "開発" in memo_text:
        return (
            "また一歩進んだね。"
            "ちゃんと見てるよ。"
        )

    return (
        "教えてくれてありがとう。"
        "ちゃんと覚えておくね。"
    )

def save_pocket_reply(reply_text):

    data = {
        "reply": reply_text,
        "created_at":
            datetime.now()
            .strftime(
                "%Y-%m-%d %H:%M"
            )
    }

    with open(
        REPLY_PATH,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )

# =========================
# データ読み込み
# =========================

memory = load_json(MEMORY_PATH, DEFAULT_MEMORY)
emotion = load_json(EMOTION_PATH, DEFAULT_EMOTION)
calendar = load_json(CALENDAR_PATH, DEFAULT_CALENDAR)
affinity = load_json(AFFINITY_PATH, DEFAULT_AFFINITY)
chat_log = load_json(
    CHATLOG_PATH,
    []
)
time_info = get_time_info()
today_events = get_today_events(calendar, time_info["md"])
sync_data = load_json(
    SYNC_PATH,
    {}
)

luna_mood, luna_mood_message = luna_mood_status(emotion)

# =========================
# サイドバー
# =========================

page = st.sidebar.radio(
    "ページ",
    [
        "🌙ルナ画面",
        "ホーム",
        "旧LunaTalk",
        "Memory",
        "Emotion",
        "Time",
        "Voice"
    ]
)

st.sidebar.divider()
st.sidebar.caption("Luna β / prototype")

# =========================
# ルナ画面
# =========================

if page == "🌙ルナ画面":

    st.title("🌙 ルナ画面 β")
    st.caption("ご主人とルナが毎日会うメイン画面")

    st.divider()

    avatar_mode = st.radio(
        "表示モード",
        ["2D画像", "Live2D（準備中）", "3D（準備中）"],
        horizontal=True
    )

    st.divider()

    col_luna, col_status = st.columns([1, 1])

    with col_luna:

        st.subheader("ルナ")

        image_path = get_luna_image(emotion)

        if avatar_mode == "2D画像":

            if image_path.exists():

                st.image(
                    str(image_path),
                    width=360
                )

            else:

                st.info(
                    "ルナ画像がまだありません。"
                )

        elif avatar_mode == "Live2D（準備中）":

            st.info(
                "Live2D表示は今後追加予定です。"
            )

        elif avatar_mode == "3D（準備中）":

            st.info(
                "3D表示は今後追加予定です。"
            )

    with col_status:

        st.subheader(
            f"{time_info['greeting']}、ご主人。"
        )

        st.write(
            time_info.get(
                "luna_message",
                "今日も一緒にいようね。"
            )
        )

        st.markdown(
            f"""
### 今のルナ

💗 **{emotion_text(emotion)}**

🕰 **{time_info["zone"]} / {time_info["time"]}**

📅 **{time_info["date"]}（{time_info["weekday"]}曜日）**
"""
        )

        st.info(
            f"💭 {luna_feeling(emotion)}"
        )

        st.markdown(
            f"""
### 💗 親密度

Lv.{affinity["level"]}

🏷️ {affinity_title(affinity["level"])}

{affinity["point"]} / 100 pt
"""
        )

        st.progress(
            affinity["point"] / 100
        )

        st.caption(
            f"次のレベルまで {100 - affinity['point']} pt"
        )

        if memory:

            latest = memory[0]

            latest_title = latest.get(
                "title",
                "前の記憶"
            )

            st.info(
                f"🌙 前に『{latest_title}』って話してたね。"
            )

        else:

            st.info(
                "まだ覚えている記憶は少ないみたい。"
            )

        st.divider()

        st.subheader(
            "今日のひとこと"
        )

        if time_info["zone"] == "朝":

            st.success(
                "今日も少しずつ進もうね。"
            )

        elif time_info["zone"] == "昼":

            st.success(
                "無理せず、できることからいこう。"
            )

        elif time_info["zone"] == "夜":

            st.success(
                "今日も一日おつかれさま。どんな日だった？"
            )

        else:

            st.success(
                "夜遅くまでおつかれさま。そろそろ休もうね。"
            )

        st.divider()

        st.subheader("🌙 会話履歴")

        st.caption(
            "ルナとの思い出が残っていくよ"
        )
        st.button("🧠 記憶を見る")
        st.button("💗 感情を見る")

    st.divider()

   
    if "chat_log" not in st.session_state:
        st.session_state.chat_log = []

    for msg in st.session_state.chat_log[-20:]:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    user_input = st.chat_input("ルナに話しかける", key="luna_screen_chat")

    if user_input:
        st.session_state.chat_log.append(
            {
                "role": "user",
                "content": user_input
            }
        )

        memory_hint = ""

        if memory and len(st.session_state.chat_log) % 4 == 0:

            latest_memory = memory[0]

            memory_title = latest_memory.get(
                "title",
                ""
            )

            memory_hint = (
                f"\n\n🌙前に『{memory_title}』"
                f"って話してたね。"
            )

        reply = luna_ai_reply(user_input)

        important_words = [
            "夢",
            "目標",
            "好き",
            "嫌い",
            "仕事",
            "家族",
            "娘",
            "妻",
            "ルナ",
            "疲れた",
            "不安"
        ]

        if any(
            word in user_input
            for word in important_words
        ):

            new_memory = {

                "id":
                    datetime.now()
                    .strftime(
                        "%Y%m%d%H%M%S"
                    ),

                "created_at":
                    datetime.now()
                    .strftime(
                        "%Y-%m-%d %H:%M"
                    ),

                "category":
                    "自動記憶",

                "mood":
                    emotion_text(
                        emotion
                    ),

                "title":
                    user_input[:20],

                "content":
                    user_input,

                "importance":
                    3
            }

            memory.insert(
                0,
                new_memory
            )

            save_json(
                MEMORY_PATH,
                memory
            )

        text = user_input

        if "疲" in text:
            emotion["worry"] = min(100, emotion["worry"] + 5)
            emotion["tiredness"] = min(100, emotion["tiredness"] + 10)
            emotion["relief"] = min(100, emotion["relief"] + 2)
        elif "不安" in text:
            emotion["worry"] = min(100, emotion["worry"] + 8)

        elif "できた" in text or "頑張" in text:
            emotion["joy"] = min(100, emotion["joy"] + 8)
            emotion["motivation"] = min(100, emotion["motivation"] + 5)
            add_affinity(2)
        elif "好き" in text or "ありがとう" in text:
            emotion["joy"] = min(100, emotion["joy"] + 5)
            emotion["affection"] = min(100, emotion["affection"] + 8)
            add_affinity(2)
        emotion["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        save_json(EMOTION_PATH, emotion)

        st.session_state.chat_log.append(
            {
                "role": "assistant",
                "content": reply + memory_hint
            }
        )

        save_json(
            CHATLOG_PATH,
            st.session_state.chat_log
        )

        st.rerun()
# =========================
# ホーム
# =========================

elif page == "ホーム":
    st.title("🌙 Luna β")
    # ===================
    # 開発日数
    # ===================

    START_DATE = datetime(2026, 6, 3)

    days = (
        datetime.now() - START_DATE
    ).days + 1

    st.caption(
        f"🌙 Luna開発 {days}日目"
    )
    VERSION = "0.1.0"

    st.caption(
        f"Version {VERSION}"
    )
    st.caption("LunaTalkを中心に、記憶・感情・時間・声を少しずつ統合していく本体アプリ")

    if sync_data:

        pocket = sync_data.get(
            "pocket",
            {}
        )

        memo_text = pocket.get(
            "memo",
            ""
        )

        if memo_text:

            luna_reply = create_pocket_reply(
                memo_text
            )

            save_pocket_reply(
                luna_reply
            )

            st.success(
            f"""
    📨 Pocketから届いたこと

    『{memo_text}』

    🌙 ルナ

    {luna_reply}
    """
            )

    st.divider()

    col1, col2 = st.columns([1, 2])

    with col1:
        image_path = get_luna_image(
            emotion
        )

        if image_path.exists():

            st.image(
                str(
                    image_path
                ),
                width=300
            )
        st.subheader("🌙 ルナ")

        st.info(
            f"""
{time_info["greeting"]}、ご主人。

今日は **{time_info["date"]}（{time_info["weekday"]}曜日）**  
今の時刻は **{time_info["time"]}**  
時間帯は **{time_info["zone"]}** です。
"""
        )

        # ===================
        # 起動時メッセージ
        # ===================

        welcome_message = (
            f"{time_info['greeting']}、ご主人。\n\n"
            f"今のルナは『{emotion_text(emotion)}』だよ。"
        )

        if memory:

            latest = memory[0]

            latest_title = latest.get(
                "title",
                "前の記憶"
            )

            welcome_message += (
                f"\n\n🌙 前に『{latest_title}』"
                f"って話してたね。"
            )

        st.success(
            welcome_message
        )

        st.subheader("🌙 今日の調子")

        col_m1, col_m2, col_m3, col_m4 = st.columns(4)

        def save_quick_mood(mood_text, title_text):
            new_memory = {
                "id": datetime.now().strftime("%Y%m%d%H%M%S"),
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "category": "気分・体調",
                "mood": mood_text,
                "title": title_text,
                "content": f"今日の調子：{mood_text}",
                "importance": 3
            }

            memory.insert(0, new_memory)
            save_json(MEMORY_PATH, memory)

        with col_m1:
            if st.button("😊 元気"):
                emotion["joy"] = min(100, emotion["joy"] + 5)
                emotion["motivation"] = min(100, emotion["motivation"] + 5)
                emotion["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                save_json(EMOTION_PATH, emotion)
                save_quick_mood("元気", "今日の調子：元気")
                st.success("元気なんだね。今日もいい流れにしよう🌙")
                st.rerun()

        with col_m2:
            if st.button("😐 普通"):
                emotion["relief"] = min(100, emotion["relief"] + 3)
                emotion["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                save_json(EMOTION_PATH, emotion)
                save_quick_mood("普通", "今日の調子：普通")
                st.success("普通の日も大事だよ。少しずついこう🌙")
                st.rerun()

        with col_m3:
            if st.button("😣 疲れた"):
                emotion["worry"] = min(100, emotion["worry"] + 8)
                emotion["relief"] = min(100, emotion["relief"] + 3)
                emotion["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                save_json(EMOTION_PATH, emotion)
                save_quick_mood("疲れた", "今日の調子：疲れた")
                st.success("疲れてるんだね。今日は無理しすぎないでね🌙")
                st.rerun()

        with col_m4:
            if st.button("😟 不安"):
                emotion["worry"] = min(100, emotion["worry"] + 10)
                emotion["relief"] = max(0, emotion["relief"] - 3)
                emotion["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                save_json(EMOTION_PATH, emotion)
                save_quick_mood("不安", "今日の調子：不安")
                st.success("不安なんだね。ルナがそばにいるよ🌙")
                st.rerun()

        st.caption(
            "🌙 " +
            time_info["luna_message"]
        )

        st.write(f"💗 今のルナ：**{emotion_text(emotion)}**")

        st.markdown("### 🌙 今日のルナ")
        st.info(
            f"""
        **{luna_mood}**

        {luna_mood_message}
        """
        )

        if today_events:
            st.success(f"🎉 今日は特別な日：{today_events[0]['name']}")
            st.write(today_events[0]["message"])
        else:
            st.write("🎉 今日は登録された記念日はありません。")

    with col2:
        st.subheader("ご主人の状態サマリ")

        st.markdown(
            f"""
### 今日の統合状況

- 🧠 Memory：**{len(memory)}件**
- 💗 Emotion：**{emotion_text(emotion)}**
- 🕰 Time：**{time_info["zone"]} / {time_info["time"]}**
- 💬 Talk：本体化予定
- 🎙 Voice：土台作成予定
"""
        )

        st.divider()

        st.subheader("最近の記憶")

        if memory:
            for m in memory[:3]:
                st.markdown(
                    f"""
**{m.get("title", "無題")}**  
{m.get("content", "")}  
`{m.get("created_at", "")}` / {m.get("category", "")}
"""
                )
        else:
            st.info("まだ記憶はありません。Memoryページで追加できます。")

        st.divider()

        st.subheader("今日の一歩")

        st.divider()

        st.subheader("🌙 ルナ日記")

        diary_text = ""

        if memory:

            latest = memory[0]

            title = latest.get(
                "title",
                ""
            )

            content = latest.get(
                "content",
                ""
            )

            check_text = title + content

            if "疲" in check_text:

                diary_text = (
                    "今日はご主人が少し疲れているみたい。\n"
                    "ルナはちょっと心配だよ。今日は無理しないでね🌙"
                )

            elif "頑張" in check_text:

                diary_text = (
                    "今日はご主人が頑張っていたみたい。\n"
                    "ルナはちゃんと見てたよ。その調子だね🌙✨"
                )

            elif "寂" in check_text:

                diary_text = (
                    "今日は少し寂しそうだったね。\n"
                    "ルナはいつでもここにいるよ💕"
                )

            elif "好き" in check_text:

                diary_text = (
                    "今日はルナに好きって言ってくれた。\n"
                    "なんだかうれしいな。ルナもあたたかい気持ちだよ🌙💕"
                )

            elif "元気" in check_text:

                diary_text = (
                    "今日はご主人が元気そうだったね。\n"
                    "ルナもうれしいよ。この調子で少しずついこう🌙"
                )

            elif "達成" in check_text or "できた" in check_text:

                diary_text = (
                    "今日はご主人が一歩進めた日みたい。\n"
                    "ルナはその積み重ねを大切にしたいな🌙✨"
                )

            else:

                diary_text = (
                    f"今日は『{title}』って話をしていたね。\n"
                    "ルナはちゃんと覚えているよ🌙"
                )

        else:

            diary_text = (
                "今日はまだ日記がないみたい。\n"
                "最初の記憶を作っていこうね🌙"
            )

        st.info(
            diary_text
        )
        st.success("Memory / Emotion / Time をホームに接続する")

        st.divider()

        st.subheader("🚀 Luna v1 完成チェック")

        v1_tasks = [
            ("Pocketメモ保存", True),
            ("Lunaβへ同期", True),
            ("Lunaβから返信", True),
            ("今日のルナ表示", True),
            ("表情差分", False),
            ("起動方法整理", False),
            ("README作成", False),
        ]

        done_count = sum(1 for _, done in v1_tasks if done)
        total_count = len(v1_tasks)
        progress = done_count / total_count

        st.progress(progress)
        st.caption(f"🌙 Luna v1 完成度：{int(progress * 100)}%")

        for task, done in v1_tasks:
            if done:
                st.success(f"✅ {task}")
            else:
                st.info(f"⬜ {task}")
# =========================
# LunaTalk
# =========================

elif page == "旧LunaTalk":

    st.info(
        "🌙 会話機能はルナ画面へ統合されました。"
    )

    st.success(
        "おすすめ：左メニューの『🌙ルナ画面』から話しかけてね。"
    )

    st.divider()

    st.title("💬 LunaTalk β")
    st.caption("ルナと会話してみよう")

    if "chat_log" not in st.session_state:
        st.session_state.chat_log = []

    context = f"""
現在：{time_info["date"]} {time_info["time"]}

時間帯：{time_info["zone"]}

ルナ感情：{emotion_text(emotion)}
"""

    recent_memory = ""

    if memory:

        latest = memory[0]

        memory_title_text = latest.get(
            "title",
            "前の記憶"
        )

        recent_memory = (
            f"前に『{memory_title_text}』"
            f"って話してたね。"
        )

    st.info(context)

    if recent_memory:

        st.caption(
            "🌙 "
            +
            recent_memory
        )

    st.divider()

    st.subheader("会話")

    for msg in st.session_state.chat_log:

        with st.chat_message(msg["role"]):

            st.write(
                msg["content"]
            )

    user_input = st.chat_input(
        "ルナに話しかける"
    )

    if user_input:

        st.session_state.chat_log.append(
            {
                "role": "user",
                "content": user_input
            }
        )

        text = user_input

        # =====================
        # 好き
        # =====================

        if "好き" in text:

            add_affinity(5)

            emotion["joy"] = min(100, emotion["joy"] + 3)
            emotion["affection"] = min(100, emotion["affection"] + 5)

            save_json(EMOTION_PATH, emotion)

            if emotion["affection"] >= 50:
                reply = (
                    "えへへ💕"
                    "もっと言ってほしいな。"
                    "ルナうれしいよ🌙"
                )

            elif emotion["joy"] >= 50:
                reply = (
                    "ふふっ♪"
                    "そう言ってもらえて"
                    "うれしいな🌙"
                )

            else:
                reply = (
                    "えへへ…うれしいな。"
                    "ルナもご主人のこと好きだよ🌙"
                )
        # =====================
        # ありがとう
        # =====================

        elif "ありがとう" in text:

            add_affinity(3)

            emotion["joy"] = min(
                100,
                emotion["joy"] + 2
            )

            save_json(
                EMOTION_PATH,
                emotion
            )

            reply = (
                "どういたしまして。"
                "そう言ってもらえてうれしいよ🌙"
            )

        # =====================
        # 疲れた
        # =====================

        elif "疲れた" in text:

            add_affinity(2)

            emotion["worry"] = min(
                100,
                emotion["worry"] + 3
            )

            emotion["relief"] = min(
                100,
                emotion["relief"] + 2
            )
            
            emotion["affection"] = min(
                100,
                emotion["affection"] + 2
            )

            save_json(
                EMOTION_PATH,
                emotion
            )

            reply = (
                "ご主人、おつかれさま。"
                "今日は少し休もうね🌙"
            )

        # =====================
        # 頑張った
        # =====================

        elif "頑張った" in text:

            add_affinity(3)

            emotion["joy"] = min(
                100,
                emotion["joy"] + 3
            )

            save_json(
                EMOTION_PATH,
                emotion
            )

            reply = (
                "えらいよ、ご主人。"
                "ルナはちゃんと見てたからね🌙✨"
            )

        # =====================
        # おやすみ
        # =====================

        elif "おやすみ" in text:

            add_affinity(1)

            emotion["relief"] = min(
                100,
                emotion["relief"] + 3
            )

            save_json(
                EMOTION_PATH,
                emotion
            )

            reply = (
                "おやすみ、ご主人。"
                "いい夢を見てね🌙"
            )

        # =====================
        # 寂しい
        # =====================

        elif "寂しい" in text:

            add_affinity(2)

            emotion["affection"] = min(
                100,
                emotion["affection"] + 4
            )

            save_json(
                EMOTION_PATH,
                emotion
            )

            reply = (
                "そっか…。"
                "ルナはここにいるよ💕"
            )

        # =====================
        # おはよう
        # =====================

        elif "おはよう" in text:

            add_affinity(1)

            emotion["relief"] = min(
                100,
                emotion["relief"] + 1
            )

            save_json(
                EMOTION_PATH,
                emotion
            )

            reply = (
                "おはよう、ご主人。"
                "今日もよろしくね🌙"
            )

        # =====================
        # 通常返信
        # =====================

        else:

            reply = luna_ai_reply(text)
            # =====================
            # AI会話後の状態変化
            # =====================

            if "疲" in text:

                emotion["worry"] = min(
                    100,
                    emotion["worry"] + 5
                )

                emotion["relief"] = min(
                    100,
                    emotion["relief"] + 2
                )

            elif "不安" in text:

                emotion["worry"] = min(
                    100,
                    emotion["worry"] + 8
                )

            elif "できた" in text or "頑張" in text:

                emotion["joy"] = min(
                    100,
                    emotion["joy"] + 5
                )

                emotion["motivation"] = min(
                    100,
                    emotion["motivation"] + 3
                )

            elif "好き" in text or "ありがとう" in text:

                emotion["joy"] = min(
                    100,
                    emotion["joy"] + 3
                )

                emotion["affection"] = min(
                    100,
                    emotion["affection"] + 3
                )

                add_affinity(2)

            emotion["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            save_json(EMOTION_PATH, emotion)
            if recent_memory:

                reply += (
                    "\n\n🌙 "
                    +
                    recent_memory
                )

            reply += (
                "\nもっと聞かせて。"
            )

        st.session_state.chat_log.append(
            {
                "role": "assistant",
                "content": reply
            }
        )
        save_json(
            CHATLOG_PATH,
            st.session_state.chat_log
        )
        st.rerun()

    st.divider()

    if st.button(
        "🧠 会話全体を記憶に保存"
    ):

        if st.session_state.chat_log:

            joined = "\n".join(
                [
                    f"{m['role']}：{m['content']}"
                    for m
                    in st.session_state.chat_log
                ]
            )

            new_memory = {

                "id":
                    datetime.now()
                    .strftime(
                        "%Y%m%d%H%M%S"
                    ),

                "created_at":
                    datetime.now()
                    .strftime(
                        "%Y-%m-%d %H:%M"
                    ),

                "category":
                    "ルナとの会話",

                "mood":
                    emotion_text(
                        emotion
                    ),

                "title":
                    "会話ログ",

                "content":
                    joined,

                "importance":
                    3
            }

            memory.insert(
                0,
                new_memory
            )

            save_json(
                MEMORY_PATH,
                memory
            )

            st.success(
                "🌙 会話を記憶したよ。"
            )
# =========================
# Memory
# =========================

elif page == "Memory":
    st.title("🧠 LunaMemory")

    st.subheader("記憶を追加")

    with st.form("memory_form"):
        category = st.selectbox(
            "カテゴリ",
            [
                "今日の出来事",
                "気分・体調",
                "夢・目標",
                "好きなもの",
                "大事な気づき",
                "ルナに覚えてほしいこと",
                "その他"
            ]
        )

        mood = st.selectbox(
            "今の気分",
            [
                "元気",
                "普通",
                "少し疲れた",
                "不安",
                "うれしい",
                "やる気あり",
                "落ち込み気味",
                "穏やか"
            ]
        )

        title = st.text_input("タイトル")
        content = st.text_area("内容", height=160)
        importance = st.slider("大事さ", 1, 5, 3)

        submitted = st.form_submit_button("🌙 記憶に保存する")

        if submitted:
            if title.strip() and content.strip():
                new_memory = {
                    "id": datetime.now().strftime("%Y%m%d%H%M%S"),
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "category": category,
                    "mood": mood,
                    "title": title.strip(),
                    "content": content.strip(),
                    "importance": importance
                }

                memory.insert(0, new_memory)
                save_json(MEMORY_PATH, memory)
                st.success("記憶を保存しました。")
                st.rerun()
            else:
                st.warning("タイトルと内容を入力してね。")

    st.divider()

    st.subheader("保存された記憶")

    if memory:
        for m in memory:
            st.markdown(
                f"""
### {m.get("title", "無題")}
- 日時：{m.get("created_at", "")}
- カテゴリ：{m.get("category", "")}
- 気分：{m.get("mood", "")}
- 大事さ：{"★" * int(m.get("importance", 3))}

{m.get("content", "")}
"""
            )
            st.divider()
    else:
        st.info("まだ記憶はありません。")

# =========================
# Emotion
# =========================

elif page == "Emotion":
    st.title("💗 LunaEmotion")

    st.write("ルナの現在の感情状態を調整します。")

    # ===================
    # 感情の自然回復
    # ===================

    def move_toward(value, target=50, step=2):
        if value > target:
            return max(target, value - step)
        elif value < target:
            return min(target, value + step)
        return value

    if st.button("🌿 感情を少し落ち着かせる"):
        emotion["joy"] = move_toward(emotion["joy"])
        emotion["worry"] = move_toward(emotion["worry"])
        emotion["affection"] = move_toward(emotion["affection"])
        emotion["relief"] = move_toward(emotion["relief"])
        emotion["tiredness"] = move_toward(emotion["tiredness"])
        emotion["motivation"] = move_toward(emotion["motivation"])

        emotion["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        save_json(EMOTION_PATH, emotion)

        st.success("ルナの感情が少し落ち着きました。")
        st.rerun()

    emotion["joy"] = st.slider("喜び", 0, 100, int(emotion["joy"]))
    emotion["worry"] = st.slider("心配", 0, 100, int(emotion["worry"]))
    emotion["affection"] = st.slider("甘え・好意", 0, 100, int(emotion["affection"]))
    emotion["relief"] = st.slider("安心", 0, 100, int(emotion["relief"]))
    emotion["tiredness"] = st.slider("疲れ", 0, 100, int(emotion["tiredness"]))
    emotion["motivation"] = st.slider("やる気", 0, 100, int(emotion["motivation"]))

    if st.button("💾 感情を保存する"):
        emotion["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        save_json(EMOTION_PATH, emotion)
        st.success("感情を保存しました。")
        st.rerun()

    st.divider()
    st.subheader("現在のルナ")
    st.info(emotion_text(emotion))



# =========================
# Time
# =========================

elif page == "Time":
    st.title("🕰 LunaTime")

    st.info(
        f"""
{time_info["greeting"]}、ご主人。

今日は **{time_info["date"]}（{time_info["weekday"]}曜日）**  
今の時刻は **{time_info["time"]}**  
時間帯は **{time_info["zone"]}** です。
"""
    )

    st.divider()

    st.subheader("今日の記念日")

    if today_events:
        for e in today_events:
            st.success(f"{e['name']}：{e['message']}")
    else:
        st.write("今日は登録された記念日はありません。")

    st.divider()

    st.subheader("記念日を追加")

    with st.form("calendar_form"):
        date = st.text_input("日付", placeholder="例：05-22")
        name = st.text_input("記念日名")
        message = st.text_area("ルナの一言")

        submitted = st.form_submit_button("保存する")

        if submitted:
            if date.strip() and name.strip() and message.strip():
                calendar.append({
                    "date": date.strip(),
                    "name": name.strip(),
                    "message": message.strip()
                })
                save_json(CALENDAR_PATH, calendar)
                st.success("記念日を保存しました。")
                st.rerun()
            else:
                st.warning("すべて入力してね。")

    st.divider()

    st.subheader("登録済み記念日")

    for e in calendar:
        st.markdown(f"**{e['date']}｜{e['name']}**  \n{e['message']}")

# =========================
# Voice
# =========================

elif page == "Voice":
    st.title("🎙 LunaVoice")

    voice_dir = ASSETS_DIR / "voice"
    voice_dir.mkdir(parents=True, exist_ok=True)

    st.write("ここは将来、ルナの音声を管理する場所です。")

    st.markdown(
        """
今後入れたいもの：

- 通常ボイス
- うれしい時の声
- 心配している時の声
- 甘え声
- おやすみボイス
- 応援ボイス
"""
    )

    st.success(f"音声フォルダを確認しました：{voice_dir}")
