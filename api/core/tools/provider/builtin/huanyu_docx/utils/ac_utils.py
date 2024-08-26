# AC 自动机快速匹配
import re
from collections import deque
import string


class Node:
    def __init__(self):
        self.children = {}
        self.fail = None
        self.is_end_of_word = False
        self.word = ""


class AcAutomation:
    def __init__(self):
        self.root = Node()

    def split_into_sentences(self, text):
        sentences = []
        # 使用正则表达式找到所有句子结束符号的位置
        sentence_ends = [match.start() for match in re.finditer(r'[\.\?!\n]', text)]

        # 添加文本末尾作为最后一个句子结束位置
        sentence_ends.append(len(text))

        # 遍历找到的所有句子结束位置
        start = 0
        for end in sentence_ends:
            # 分割出每个句子，并去除首尾空白字符
            sentence = text[start:end + 1].strip()
            if sentence:  # 如果句子非空，则添加到列表中
                sentences.append(sentence)
            start = end + 1

        return sentences
    def insert_trie(self, word):
        node = self.root
        for char in word:
            if char not in node.children:
                node.children[char] = Node()
            node = node.children[char]
        node.is_end_of_word = True
        node.word = word

    def build_ac_automaton(self):
        queue = deque([self.root])
        while queue:
            current = queue.popleft()
            for char, child in current.children.items():
                queue.append(child)
                fail = current.fail
                while fail and char not in fail.children:
                    fail = fail.fail
                child.fail = fail.children[char] if fail else self.root
                if child.fail.is_end_of_word:
                    child.is_end_of_word = True

    def search_ac_automaton(self, text):
        # 分割文本为句子
        sentences = self.split_into_sentences(text)

        # 保存每个句子的起始位置
        sentence_starts = {len(''.join(sentences[:i])): sentence for i, sentence in enumerate(sentences)}

        # 查找匹配并保存所在句子
        matches_with_sentences = []
        node = self.root
        for i in range(len(text)):
            while node and text[i] not in node.children:
                node = node.fail
            if not node:
                node = self.root
                continue
            node = node.children[text[i]]
            temp_node = node
            while temp_node:
                if temp_node.is_end_of_word:
                    start_index = i - len(temp_node.word) + 1
                    # 检查是否是英文字母为边界，缩略词不可能存在于单词中
                    if not (start_index > 0 and text[start_index - 1] in string.ascii_letters) and \
                            not (start_index + len(temp_node.word) < len(text) and text[
                                start_index + len(temp_node.word)] in string.ascii_letters):
                        # 寻找该单词所在句子
                        sentence_start = max(start for start in sentence_starts.keys() if start <= start_index)
                        sentence = sentence_starts[sentence_start]
                        matches_with_sentences.append((start_index, temp_node.word, sentence))
                temp_node = temp_node.fail
        return matches_with_sentences

    def find_matches(self, text, words):
        for word in words:
            self.insert_trie(word)
        self.build_ac_automaton()
        return self.search_ac_automaton(text)

# Example usage
# root = Node()
# words = ["actf", "tf", "f", "wi", "with"]
# for word in words:
#     insert_trie(root, word)
# build_ac_automaton(root)
# text = "text with actf and acttf"
# matches = search_ac_automaton(text, root)
# print("Matches:", matches)
