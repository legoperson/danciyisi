# vocab_test.py
import random
import pandas as pd
from typing import List, Dict, Any


def generate_mcq_questions(
    df: pd.DataFrame,
    n_questions: int = 10,
    n_options: int = 4
) -> List[Dict[str, Any]]:
    """
    从词汇表中生成选择题。
    每道题：1 个单词 + 4 个选项（1 个正确释义 + 3 个错误释义）。

    df 需要有两列: 'word', 'meaning'
    """
    if "word" not in df.columns or "meaning" not in df.columns:
        raise ValueError("DataFrame 必须包含 'word' 和 'meaning' 两列")

    df = df.dropna(subset=["word", "meaning"]).reset_index(drop=True)
    if df.empty:
        raise ValueError("词汇表为空")

    n_questions = min(n_questions, len(df))

    # 随机选出要出题的单词
    question_rows = df.sample(n=n_questions, replace=False).reset_index(drop=True)

    questions = []
    for _, row in question_rows.iterrows():
        word = str(row["word"])
        correct = str(row["meaning"])

        # 选出错误选项（其他单词的释义）
        other_meanings = df[df["word"] != word]["meaning"]
        if len(other_meanings) < (n_options - 1):
            # 词太少，退一步用全表的释义（去重）
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
