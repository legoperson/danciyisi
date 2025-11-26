# vocab_test.py
import random
import pandas as pd
from typing import List, Dict, Any, Optional


def generate_mcq_questions(
    df: pd.DataFrame,
    n_questions: int = 10,
    n_options: int = 4,
    words: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    从词汇表中生成选择题。
    每道题：1 个单词 + 4 个选项（1 个正确释义 + 3 个错误释义）。

    参数:
    - df: 必须包含 'word', 'meaning' 两列的 DataFrame（整个词汇表）
    - n_questions: 题目数量（如果 words 不为空则忽略）
    - n_options: 选项个数（默认 4）
    - words: 如果提供，则只用这些单词来出题（题目顺序随机）

    返回:
    - questions: List[dict]，每个 dict:
        {
            "word": str,
            "correct": str,
            "options": List[str]
        }
    """
    if "word" not in df.columns or "meaning" not in df.columns:
        raise ValueError("DataFrame 必须包含 'word' 和 'meaning' 两列")

    df = df.dropna(subset=["word", "meaning"]).reset_index(drop=True)
    if df.empty:
        raise ValueError("词汇表为空")

    # 决定用哪些 word 出题
    if words is not None:
        # 限制在 df 中确实存在的单词
        base_df = df[df["word"].isin(words)].drop_duplicates(subset=["word"])
        if base_df.empty:
            raise ValueError("提供的 words 在 DataFrame 中找不到")
        # 打乱顺序
        base_df = base_df.sample(frac=1.0, replace=False).reset_index(drop=True)
    else:
        n_questions = min(n_questions, len(df))
        base_df = df.sample(n=n_questions, replace=False).reset_index(drop=True)

    questions: List[Dict[str, Any]] = []

    for _, row in base_df.iterrows():
        word = str(row["word"])
        correct = str(row["meaning"])

        # 选出错误选项（其他单词的释义）
        other_meanings = df[df["word"] != word]["meaning"]
        if len(other_meanings) < (n_options - 1):
            # 词太少，退一步用全表的释义
            other_meanings = df["meaning"]

        wrongs = (
            other_meanings.sample(n=n_options - 1, replace=False)
            .astype(str)
            .tolist()
        )

        options = wrongs + [correct]
        random.shuffle(options)

        questions.append(
            {
                "word": word,
                "correct": correct,
                "options": options,
            }
        )

    return questions
