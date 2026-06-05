import streamlit as st
import json
from pathlib import Path
from datetime import datetime

# =========================
# 基本設定
# =========================

APP_TITLE = "LunaMemory β"
DATA_DIR = Path("data")
MEMORY_PATH = DATA_DIR / "luna_memory.json"

DATA_DIR.mkdir(exist_ok=True)

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🌙",
    layout="centered"
)

# =========================
# CSS
# =========================

st.markdown(
    """
    <style>
    .main {
        background: linear-gradient(180deg, #fff7fb 0%, #f7f3ff 100%);
    }
    .title-box {
        padding: 24px;
        border-radius: 24px;
        background: rgba(255,255,255,0.85);
        box-shadow: 0 8px 24px rgba(120, 90, 160, 0.12);
        margin-bottom: 20px;
    }
    .memory-card {
        padding: 18px;
        border-radius: 18px;
        background: white;
        box-shadow: 0 4px 16px rgba(120, 90, 160, 0.10);
        margin-bottom: 14px;
        border-left: 6px solid #c9a7ff;
    }
    .small-text {
        color: #777;
        font-size: 0.9rem;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# =========================
# データ処理
# =========================

def load_memories():
    if MEMORY_PATH.exists():
        try:
            with open(MEMORY_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_memories(memories):
    with open(MEMORY_PATH, "w", encoding="utf-8") as f:
        json.dump(memories, f, ensure_ascii=False, indent=2)


def add_memory(category, mood, title, content, importance):
    memories = load_memories()

    new_memory = {
        "id": datetime.now().strftime("%Y%m%d%H%M%S"),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "category": category,
        "mood": mood,
        "title": title,
        "content": content,
        "importance": importance,
        "for_luna": True
    }

    memories.insert(0, new_memory)
    save_memories(memories)


# =========================
# 画面
# =========================

st.markdown(
    f"""
    <div class="title-box">
        <h1>🌙 {APP_TITLE}</h1>
        <p>
        ルナがご主人のことを少しずつ覚えていくための記憶ノートです。<br>
        今日の出来事、気持ち、夢、覚えてほしいことをここに残していきます。
        </p>
    </div>
    """,
    unsafe_allow_html=True
)

tab1, tab2, tab3 = st.tabs(["📝 記憶を残す", "📖 記憶を見る", "🌙 ルナ用まとめ"])

# =========================
# 記憶を残す
# =========================

with tab1:
    st.subheader("📝 ルナに覚えてほしいこと")

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

    title = st.text_input("タイトル", placeholder="例：今日はLunaMemoryを作り始めた")

    content = st.text_area(
        "内容",
        placeholder="ルナに覚えてほしいことを書いてね。",
        height=180
    )

    importance = st.slider("大事さ", 1, 5, 3)

    if st.button("🌙 ルナの記憶に保存する"):
        if title.strip() and content.strip():
            add_memory(category, mood, title, content, importance)
            st.success("保存しました。ルナの記憶がひとつ増えました🌙")
            st.rerun()
        else:
            st.warning("タイトルと内容を入力してね。")

# =========================
# 記憶を見る
# =========================

with tab2:
    st.subheader("📖 保存された記憶")

    memories = load_memories()

    if not memories:
        st.info("まだ記憶はありません。まずはひとつ残してみよう。")
    else:
        filter_category = st.selectbox(
            "カテゴリで絞り込み",
            ["すべて"] + sorted(list(set(m["category"] for m in memories)))
        )

        if filter_category != "すべて":
            memories = [m for m in memories if m["category"] == filter_category]

        for m in memories:
            st.markdown(
                f"""
                <div class="memory-card">
                    <div class="small-text">{m["created_at"]} / {m["category"]} / 気分：{m["mood"]}</div>
                    <h3>{m["title"]}</h3>
                    <p>{m["content"]}</p>
                    <div class="small-text">大事さ：{"★" * int(m["importance"])}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

# =========================
# ルナ用まとめ
# =========================

with tab3:
    st.subheader("🌙 LunaTalkへ渡す用の記憶まとめ")

    memories = load_memories()

    if not memories:
        st.info("まだまとめる記憶がありません。")
    else:
        latest_count = st.slider("まとめる記憶の数", 1, min(20, len(memories)), min(5, len(memories)))

        selected = memories[:latest_count]

        summary_text = "以下は、ご主人についてルナが覚えておくべき記憶です。\n\n"

        for m in selected:
            summary_text += f"- 日時：{m['created_at']}\n"
            summary_text += f"  カテゴリ：{m['category']}\n"
            summary_text += f"  気分：{m['mood']}\n"
            summary_text += f"  タイトル：{m['title']}\n"
            summary_text += f"  内容：{m['content']}\n"
            summary_text += f"  大事さ：{m['importance']}/5\n\n"

        st.text_area(
            "LunaTalkのプロンプトに入れる用",
            value=summary_text,
            height=300
        )

        st.download_button(
            "📥 記憶まとめをダウンロード",
            data=summary_text,
            file_name="luna_memory_summary.txt",
            mime="text/plain"
        )
