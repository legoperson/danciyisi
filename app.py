# app.py
import random
from typing import List, Dict, Any

import pandas as pd
import streamlit as st

from vocab_test import generate_mcq_questions


st.set_page_config(page_title="Year 5 Vocabulary Practice", page_icon="📚", layout="wide")


# -------------------------
# 辅助函数
# -------------------------
def init_session_state():
    if "df" not in st.session_state:
        st.session_state.df = None
    if "current_idx" not in st.session_state:
        st.session_state.current_idx = None
    if "questions" not in st.session_state:
        st.session_state.questions = None
    if "show_result" not in st.session_state:
        st.session_state.show_result = False
    if "answers" not in st.session_state:
        st.session_state.answers = {}  # {q_idx: user_option}


def pick_random_word():
    df = st.session_state.df
    if df is None or df.empty:
        return
    st.session_state.current_idx = random.randint(0, len(df) - 1)


def start_test(num_questions: int):
    df = st.session_state.df
    if df is None or df.empty:
        st.warning("请先上传并成功读取 CSV 文件。")
        return
    try:
        questions = generate_mcq_questions(df, n_questions=num_questions, n_options=4)
    except Exception as e:
        st.error(f"生成测试题失败: {e}")
        return

    st.session_state.questions = questions
    st.session_state.show_result = False
    st.session_state.answers = {}


# -------------------------
# 主程序
# -------------------------
def main():
    init_session_state()

    st.title("📚 Year 5 Vocabulary Practice")
    st.write("上传你刚才生成的 CSV（word_list.csv），然后练习单词。")

    # 文件上传
    uploaded_file = st.file_uploader("上传词汇 CSV 文件", type=["csv"])
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            if "word" not in df.columns or "meaning" not in df.columns:
                st.error("CSV 必须包含列：'word' 和 'meaning'")
                return
            st.session_state.df = df.dropna(subset=["word", "meaning"]).reset_index(drop=True)
        except Exception as e:
            st.error(f"读取 CSV 出错: {e}")
            return

    if st.session_state.df is None:
        st.info("请先上传 CSV 文件。")
        return

    df = st.session_state.df

    # -------------------------
    # 左侧：随机看词 + 释义
    # -------------------------
    col1, col2 = st.columns([1, 2])

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
    # 右侧：测试部分
    # -------------------------
    with col2:
        st.subheader("📝 Test 模式（选择题）")

        num_questions = st.number_input(
            "题目数量",
            min_value=3,
            max_value=min(30, len(df)),
            value=min(10, len(df)),
            step=1,
        )

        if st.button("开始 / 重做 Test"):
            start_test(num_questions)

        questions: List[Dict[str, Any]] = st.session_state.questions

        if questions:
            st.markdown("---")
            st.markdown("### 选择正确的释义")

            # 显示每一道题
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

            # 提交答案
            if st.button("提交答案"):
                st.session_state.show_result = True

            if st.session_state.show_result:
                correct_count = 0
                total = len(questions)
                st.markdown("### ✅ 结果")

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


if __name__ == "__main__":
    main()
