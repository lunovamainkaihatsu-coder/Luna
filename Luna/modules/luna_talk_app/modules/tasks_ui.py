import json
from typing import List, Tuple

import streamlit as st
from openai import OpenAI

from .tasks_store import (
    ensure_task_shape,
    add_task,
    delete_done_tasks,
    save_tasks,
)


def pick_focus_tasks_ai(client: OpenAI, tasks: List[dict], profile: dict) -> Tuple[List[str], str]:
    """
    tasksから今日の3つをAIに選ばせる（テキストのリストを返す）
    """
    tasks = ensure_task_shape(tasks)

    if not tasks:
        return [], "ご主人、タスクがまだないみたいです。まずは1つだけ登録してみましょう？"

    call_name = profile.get("call_name", "ご主人")
    task_texts = [t["text"] for t in tasks if not t.get("done", False)]

    if not task_texts:
        return [], f"{call_name}、全部完了してます…！今日は休んでいい日ですよ。えらい。"

    # 長文回避
    task_texts = task_texts[:30]

    system_prompt = f"""
あなたは「ルナ」。{call_name}に寄り添う相棒です。
目的：マルチタスクで迷う{call_name}のために、「今日やる3つ」だけを選びます。

必ずJSONだけを返してください：
{{
  "focus": ["今日やるタスク1", "今日やるタスク2", "今日やるタスク3"],
  "comment": "ルナの一言（短く、やさしく）"
}}

ルール：
- focusは最大3つ。少ないなら1〜2でもOK
- {call_name}を責めない
- 重いタスクが多い場合は「軽いのを混ぜる」
- commentは1文でOK
"""

    user_prompt = "候補タスク一覧:\n" + "\n".join([f"- {x}" for x in task_texts])

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

        focus = data.get("focus", [])
        comment = str(data.get("comment", "")).strip()

        focus = [str(x).strip() for x in focus if str(x).strip()][:3]
        if not comment:
            comment = f"{call_name}、今日はこの3つだけで十分ですよ。"

        return focus, comment

    except Exception as e:
        print("Focus AI Error:", e)
        focus = task_texts[:3]
        comment = f"{call_name}、今日はまずこのあたりからいきましょう。"
        return focus, comment


def init_tasks_state():
    """
    tasks周りの session_state 初期化
    """
    if "tasks" not in st.session_state:
        st.session_state.tasks = []
    st.session_state.tasks = ensure_task_shape(st.session_state.tasks)

    if "focus_tasks" not in st.session_state:
        st.session_state.focus_tasks = []
    if "focus_comment" not in st.session_state:
        st.session_state.focus_comment = ""


def render_tasks_sidebar(client: OpenAI, tasks_path, profile: dict):
    """
    サイドバーUI（追加・チェック・削除・今日の3つ）
    永続化はここでsave_tasksを呼んで担保する。
    """
    init_tasks_state()

    with st.sidebar:
        st.markdown("### 📝 ルナのタスクインボックス")

        # 新規タスク入力
        new_task = st.text_input("あとでやりたいことをメモ", key="task_input")

        col_a, col_b = st.columns(2)

        with col_a:
            if st.button("追加"):
                if new_task.strip():
                    st.session_state.tasks = add_task(st.session_state.tasks, new_task)
                    save_tasks(tasks_path, st.session_state.tasks)
                    st.rerun()

        with col_b:
            if st.button("🤝 今日の3つを決める（AI）"):
                focus, comment = pick_focus_tasks_ai(client, st.session_state.tasks, profile)
                st.session_state.focus_tasks = focus
                st.session_state.focus_comment = comment
                st.rerun()

        # 今日の3つ表示（固定）
        if st.session_state.focus_tasks:
            st.markdown("---")
            st.markdown("### ✅ 今日の3つ（固定）")
            for j, t in enumerate(st.session_state.focus_tasks, start=1):
                st.write(f"{j}. {t}")
            if st.session_state.focus_comment:
                st.caption(f"ルナ：{st.session_state.focus_comment}")

        st.markdown("---")
        st.markdown("#### 登録中のタスク")

        if not st.session_state.tasks:
            st.caption("（まだタスクはありません）")
            return

        # 既存タスクのチェックボックス（idで安定key）
        changed = False
        for task in st.session_state.tasks:
            k = f"task_{task['id']}"
            checked = st.checkbox(task["text"], value=task.get("done", False), key=k)
            if task.get("done", False) != checked:
                task["done"] = checked
                changed = True

        # チェック状態が変わったら保存
        if changed:
            save_tasks(tasks_path, st.session_state.tasks)

        # 完了タスク削除
        if st.button("完了したタスクを消す"):
            st.session_state.tasks = delete_done_tasks(st.session_state.tasks)
            save_tasks(tasks_path, st.session_state.tasks)
            st.rerun()
