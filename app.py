# app.py
import random
from typing import List, Dict, Any

import pandas as pd
import streamlit as st
import requests
from googletrans import Translator

from vocab_test import generate_mcq_questions

st.set_page_config(
    page_title="Year 5 Vocabulary Practice",
    page_icon="📚",
    layout="wide",
)

# 本地 CSV 路径：第一列单词，第二列可以是原始释义（可有可无）
CSV_PATH = "word_list.csv"

# 全局翻译器
translator = Translator()


# -------------------------
# 词典 & 翻译函数
# -------------------------
def fetch_meaning_for_word(word: str) -> str:
    """
    根据单词从在线字典 API 拉一个简短英文释义。
    使用 https://api.dictionaryapi.dev/ 这个公开接口。
    出错或查不到时返回空字符串。
    """
    if not word:
        return ""
    try:
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
        resp = requests.get(url, timeout=5)
        if resp.status_code != 200:
            return ""
        data = resp.json()
        if not isinstance(data, list) or not data:
            return ""
        first = data[0]
        meanings = first.get("meanings", [])
        if not meanings:
            return ""
        defs = meanings[0].get("definitions", [])
        if not defs:
            return ""
        definition = defs[0].get("definition", "")
        return definition.strip()
    except Exception:
        return ""


def translate_to_zh(text: str) -> str:
    """
    把英文释义翻译成中文。
    失败时返回空字符串，不抛异常。
    """
    if not text:
        return ""
    try:
        result = translator.translate(text, dest="zh-cn")
        return result.text.strip()
    except Exception:
        return ""


def ensure_meanings(df: pd.DataFrame) -> pd.DataFrame:
    """
    对所有行都做一次更新：
    - 无论原 meaning 有没有值，都尝试按 word 重新查一次英文释义 new_en；
    - 如果 new_en 为空，则用原来的 old_meaning 兜底；
    - 在 final_en 的基础上翻译成中文 zh；
    - 最终 meaning 列为: "final_en（zh）"，若 zh 为空则只有 final_en。

    这样可以：
    - 尽量修正 PDF 提取导致的不完整释义；
    - 查不到的词又不会丢掉你原来写在 CSV 里的内容。
    """
    if "word" not in df.columns:
        raise ValueError("CSV 必须至少有一列为单词列，且列名为 'word'。")

    # 如果没有 meaning 列，就先创建
    if "meaning" not in df.columns:
        df["meaning"] = ""

    new_meanings: List[str] = []

    for _, row in df.iterrows():
        word = str(row["word"]).strip()

        old_meaning = row["meaning"]
        if pd.isna(old_meaning):
            old_meaning = ""
        old_meaning = str(old_meaning).strip()

        # 1. 尝试查新的英文释义
        new_en = fetch_meaning_for_word(word)

        # 2. 查不到就用原来的
        final_en = new_en if new_en else old_meaning

        # 3. 翻译成中文
        zh = translate_to_zh(final_en) if final_en else ""

        # 4. 组合
        if final_en and zh:
            combined = f"{final_en}（{zh}）"
        else:
            combined = final_en

        new_meanings.append(combined)

    df["meaning"] = new_meanings
    return df


# -------------------------
# Session state 初始化
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
        # "idle" | "study" | "test"
        st.session_state.phase = "idle"


# -------------------------
# 读本地 CSV
# -------------------------
def load_local_csv():
    """
    从本地 CSV 读取：
    - 把第一列当作单词列，列名改成 'word'；
    - 第二列若存在，当作原始 meaning 兜底；
    - 然后调用 ensure_meanings 统一更新+加中文。
    """
    try:
        df = pd.read_csv(CSV_PATH)
    except Exception as e:
        st.error(f"读取本地文件 `{CSV_PATH}` 失败：{e}")
        return None

    # 如果没有 'word' 列，则自动把第一列命名为 'word'
    if "word" not in df.columns:
        # 把第一列重命名为 word
        first_col = df.columns[0]
        df = df.rename(columns={first_col: "word"})

    # 若 meaning 列不存在而且有第二列，就把第二列当作 meaning
    if "meaning" not in df.columns and df.shape[1] >= 2:
        second_col = df.columns[1]
        df = df.rename(columns={second_col: "meaning"})

    try:
        df = ensure_meanings(df)
    except Exception as e:
        st.error(f"处理单词与释义时出错：{e}")
        return None

    return df[["word", "meaning"]].dropna(subset=["word"]).reset_index(drop=True)


# -------------------------
# 随机单词学习
# -------------------------
def pick_random_word():
    df = st.session_state.df
    if df is None or df.empty:
        return
    st.session_state.current_idx = random.randint(0, len(df) - 1)


# -------------------------
# Test 流程
# -------------------------
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
            words=words,
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
    st.write(
        "从本地 `word_list.csv` 读取单词："
        "第一列作为单词，第二列（如果有）作为原始释义。"
        "程序会自动按单词更新英文释义，并附上中文解释。"
    )

    # 读取本地 CSV，只读一次
    if st.session_state.df is None:
        df = load_local_csv()
        if df is not None:
            st.session_state.df = df

    if st.session_state.df is None:
        st.stop()

    df = st.session_state.df

    col1, col2 = st.columns([1, 2])

    # 左侧：随机单词学习
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

    # 右侧：Test 模式
    with col2:
        st.subheader("📝 Test 模式（先看单词，再做题）")

        num_questions = st.number_input(
            "本次想练习多少个单词？",
            min_value=3,
            max_value=min(50, len(df)),
            value=min(10, len(df)),
            step=1,
        )

        if st.button("抽取并显示这批单词"):
            prepare_study_list(int(num_questions))

        # 记忆阶段：显示 word + meaning 列表
        if st.session_state.phase == "study" and st.session_state.study_df is not None:
            study_df = st.session_state.study_df
            st.markdown("### 请先记忆这些单词（显示 word + meaning）")

            for i, row in study_df.iterrows():
                st.markdown(f"**{i+1}. {row['word']}** — {row['meaning']}")

            st.markdown("---")
            if st.button("开始 Test（隐藏上面列表）"):
                start_test_from_study()

        # Test 阶段：只给选择题，不再显示原释义
        questions: List[Dict[str, Any]] = st.session_state.questions

        if st.session_state.phase == "test" and questions:
            st.markdown("### 选择题 Test")
            st.markdown("为每个单词选择正确的释义（英文 + 中文）。")

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
                    f"**总分：{correct_count} / {total}**  "
                    f"（正确率：{correct_count/total*100:.1f}%）"
                )

                wrong_words = [
                    q["word"]
                    for i, q in enumerate(questions)
                    if st.session_state.answers.get(i, None) != q["correct"]
                ]
                if wrong_words:
                    st.markdown("**本次做错的单词：** " + ", ".join(wrong_words))


if __name__ == "__main__":
    main()
