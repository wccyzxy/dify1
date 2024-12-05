import re
from typing import Optional
from pathlib import Path

import jieba
from jieba.analyse import default_tfidf


class JiebaKeywordTableHandler:
    def __init__(
            self,
            user_dict_filename: Optional[str] = "user_dict.txt",
            stop_words_filename: Optional[str] = "stop_words.txt"
    ):
        current_dir = Path(__file__).parent
        self.stop_words = set()
        stop_words_path = current_dir / stop_words_filename
        if stop_words_path.exists():
            self._load_stop_words(str(stop_words_path))

        # 设置停用词
        default_tfidf.stop_words = self.stop_words

        # 加载用户词典
        user_dict_path = current_dir / user_dict_filename
        if user_dict_path.exists():
            jieba.load_userdict(str(user_dict_path))

    def _load_stop_words(self, stop_words_path: str) -> None:
        """加载停用词文件"""
        try:
            with open(stop_words_path, 'r', encoding='utf-8') as f:
                # 每行一个停用词
                custom_stop_words = {line.strip() for line in f if line.strip()}
                self.stop_words.update(custom_stop_words)
        except Exception as e:
            print(f"加载停用词文件失败: {e}")

    def extract_keywords(self, text: str, max_keywords_per_chunk: Optional[int] = 30) -> set[str]:
        """Extract keywords with JIEBA tfidf."""
        keywords = jieba.analyse.extract_tags(
            sentence=text.replace(" ", ""),
            topK=max_keywords_per_chunk,
        )

        return set(self._expand_tokens_with_subtokens(keywords))

    def _expand_tokens_with_subtokens(self, tokens: set[str]) -> set[str]:
        """Get subtokens from a list of tokens., filtering for stopwords."""
        results = set()
        for token in tokens:
            results.add(token)
            sub_tokens = re.findall(r"\w+", token)
            if len(sub_tokens) > 1:
                results.update({w for w in sub_tokens if w not in list(self.stop_words)})

        return results