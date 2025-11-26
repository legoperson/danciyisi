import random
from typing import List, Dict, Any

import pandas as pd
import streamlit as st
import requests

from vocab_test import generate_mcq_questions

# 尝试导入 googletrans，失败就不做中文翻译
try:
    from googletrans import Translator  # type: ignore

    translator = Translator()
except Exception:
    translator = None  # 没有翻译器也能跑，只是没有中文

st.set_page_config(
    page_title="Year 5 Vocabulary Practice",
    page_icon="📚",
    layout="wide",
)

# 本地 CSV 路径：第一列单词，第二列可以是原始释义（可有可无）
CSV_PATH = "word_list.csv"


# -------------------------
# 词典 & 翻译函数
# -------------------------
def fetch_meaning_for_word(word: str) -> str:
    """
    根据单词从在线字典 API 拉一个简短英文释义。
    https://api.dictionaryapi.dev/
    出错或查不到时返回空字符串。
    """
    word = word.strip()
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
        if not def
