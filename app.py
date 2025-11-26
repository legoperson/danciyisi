# app.py
import random
from typing import List, Dict, Any

import pandas as pd
import streamlit as st

from vocab_test import generate_mcq_questions


st.set_page_config(page_title="Year 5 Vocabulary Practice", page_icon="📚", layout="wide")

# 本地 CSV 路径（你可以按需要改名）
CSV_PATH = "word_list.csv"


# -------------------------
# 辅助函数：初始化 session_state
# -------------------------
def init_session_state():
    if "df" not in st.session_state:
        st.session_state.df = None

    if "current_idx" not in st.session_state:
        st.session_state.current_idx = None

    if "questions" not in st.session_state:
        st.session_state.questions: List[Dict[str, Any]] = None

    if "show_result" not in st.session_state:
        st.session_state.show_result = False

    if "answers" not in st.session_state:
        st.session_state.answers = {}  # {q_idx: user_option}

    if "study_df" not in st.session_state:
        st.session_state.study_df = None  # 本次要考的那批单词（带释义）

    if "phase" not in st.session_state:
        # phase: "idle" | "study" | "test"
        st.session_state.phase = "idle"


def load_local_csv():
    """从本地 CSV 读取 word_list."""
    try:
        df = pd.read_csv(CSV_PATH)
    except Exception as e:
        st.error(f"读取本地文件 `{CSV_PATH}` 失败：{e}")
        return None

    if "word" not in df.columns or "meaning" not in df.columns:
        st.error(f"CSV 必须包含列：'word' 和 'meaning'。当前列为：{list(df.columns)}")
        return None

    return df.dropna(subset=["word", "meaning"]).reset_index(drop=True)


def pick_random_word():
    """左侧：随机选一个单词展示。"""
    df = st.session_state.df
    if df is None or df.empty:
        return
    st.session_state.current_idx = random.randint(0, len(df) - 1)


def prepare_study_list(num_questions: int):
    """
    抽取一批单词供记忆，并显示 word + meaning。
    后续开始 Test 时，就只考这批单词。
    """
    df = st.session_state.df
    if df is None or df.empty:
        st.warning("请先确保本地 CSV 读取成功。")
        return

    n = min(num_questions, len(df))
    st.session_state.study_df = df.sample(n=n, replace=False).reset_index(drop=True)

    # 进入“记忆阶段”
    st.session_state.phase = "study"
    st.session_state.questions = None
    st.session_state.show_result = False
    st.session_state.answers = {}


def start_test_from_study():
    """
    根据当前 study_df 里的单词生成选择题。
    进入 Test 阶段，隐藏原来的 word+meaning 列表。
    """
    df_full = st.session_state.df
    study_df = st.session_state.study_df

    if df_full is None or df_full.empty:
        st.warning("词汇表为空，请检查 CSV。")
        return

    if study_df is None or study_df.empty:
        st.warning("还没有抽取要考的单词，请先点击『抽取并显示这批单词』。")
        return

    words = study_df["word"].astype(str).tolist()

    try:
        questions = generate_mcq_questions(
            df_full,
            n_options=4,
            words=words,        # 只考这批单词
        )
    except Exception as e:
        st.error(f"生成测试题失败: {e}")
        return

    st.session_state.questions = questions
    st.session_state.phase = "test"
    st.session_state.show_result = False
    st.session_state.answers = {}


# -------------------------
# 主程序
# -------------------------
def main():
    init_session_state()

    st.title("📚 Year 5 Vocabulary Practice")
    st.write("直接从本地 `word_list.csv` 读取单词（包含列 `word`, `meaning`）。")

    # 读取本地 CSV，只读一次
    if st.session_state.df is None:
        df = load_local_csv()
        if df is not None:
            st.session_state.df = df

    if st.session_state.df is None:
        st.stop()

    df = st.session_state.df

    # 布局：左随机单词 + 右测试模块
    col1, col2 = st.columns([1, 2])

    # -------------------------
    # 左侧：随机单词学习
    # -------------------------
    with col1:
        st.subheader("🔍 随机单词学习")

        if st.session_state.current_idx is None:
            pick_random_word()

        if st.button("换一个随机单词"):
            pick_random_word()

        if st.session_state.current_idx is not None:
            row = df.iloc[st.session_state.current_idx]
            st.markdown(f"### 单词：**{row['word']}**")
            st.markdown(f"**释义：** {row['meaning']}")

    # -------------------------
    # 右侧：Test 模块
    # -------------------------
    with col2:
        st.subheader("📝 Test 模式（先看单词，再做题）")

        num_questions = st.number_input(
            "本次想练习多少个单词？",
            min_value=3,
            max_value=min(50, len(df)),
            value=min(10, len(df)),
            step=1,
        )

        # 第一步：抽取并显示单词+释义
        if st.button("抽取并显示这批单词"):
            prepare_study_list(int(num_questions))

        # 记忆阶段：显示这批单词和释义
        if st.session_state.phase == "study" and st.session_state.study_df is not None:
            study_df = st.session_state.study_df
            st.markdown("### 请先记忆这些单词（显示 word + meaning）")

            for i, row in study_df.iterrows():
                st.markdown(f"**{i+1}. {row['word']}** — {row['meaning']}")

            st.markdown("---")
            if st.button("开始 Test（隐藏上面列表）"):
                start_test_from_study()

        # 测试阶段：只显示选择题，不再显示原始释义
        questions: List[Dict[str, Any]] = st.session_state.questions

        if st.session_state.phase == "test" and questions:
            st.markdown("### 选择题 Test（不再显示原始释义）")
            st.markdown("为每个单词选择正确的释义。")

            for i, q in enumerate(questions):
                st.markdown(f"**Q{i+1}. {q['word']}**")
                key = f"q_{i}"
                user_choice = st.radio(
                    "选择释义：",
                    q["options"],
                    key=key,
                    index=None,
                    horizontal=False,
                )
                if user_choice is not None:
                    st.session_state.answers[i] = user_choice
                st.markdown("---")

            if st.button("提交答案"):
                st.session_state.show_result = True

            if st.session_state.show_result:
                correct_count = 0
                total = len(questions)
                st.markdown("### ✅ 本次结果")

                for i, q in enumerate(questions):
                    user_ans = st.session_state.answers.get(i, None)
                    correct = q["correct"]

                    if user_ans == correct:
                        correct_count += 1
                        st.success(f"Q{i+1}: 正确 ✅")
                    else:
                        st.error(
                            f"Q{i+1}: 错误 ❌\n\n"
                            f"- 你的选择: {user_ans}\n"
                            f"- 正确答案: {correct}"
                        )

                st.markdown(
                    f"**总分：{correct_count} / {total}**  （正确率：{correct_count/total*100:.1f}%）"
                )

                # 方便你重新记这批错误题
                wrong_words = [
                    q["word"]
                    for i, q in enumerate(questions)
                    if st.session_state.answers.get(i, None) != q["correct"]
                ]
                if wrong_words:
                    st.markdown("**本次做错的单词：** " + ", ".join(wrong_words))


if __name__ == "__main__":
    main()
