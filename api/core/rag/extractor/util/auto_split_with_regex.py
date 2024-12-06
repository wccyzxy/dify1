import re
import logging
from typing import List, Dict, Optional, Set, Tuple, Any
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ParseResult:
    """Data class to store parsing results for each paragraph"""
    content: str
    marker_levels: Optional[Dict[int, int]]
    error: Optional[str] = None


@dataclass
class DocumentNode:
    """Data class to represent a document node in the tree structure"""
    block: str = ""  # The block header/marker text
    content: str = ""  # The content text
    children: List['DocumentNode'] = field(default_factory=list)
    marker_type: Optional[int] = None  # The type of marker (if any)
    level: Optional[int] = None  # The hierarchical level


class DocumentStructureParser:
    """
    A class to parse and analyze document structure based on various marker patterns
    (like chapter numbers, section numbers, etc.)
    """

    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)

        # Configure logging
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

        # Paragraph separator patterns
        self._compile_paragraph_patterns()

        # Marker patterns with hierarchy levels
        self._compile_marker_patterns()

    def _compile_paragraph_patterns(self) -> None:
        """Compile regex patterns for paragraph separation"""
        patterns = [
            r'^附件$',  # 精确匹配"附件"
            r'^附\s*\d+$',  # 匹配"附1"或"附 1"
            r'^附\s*\d+-\d+$',  # 匹配"附1-1"或"附 1-1"
        ]
        self.paragraph_patterns = [re.compile(pattern) for pattern in patterns]

    def _compile_marker_patterns(self) -> None:
        """Compile regex patterns for marker identification"""
        self.marker_patterns = [
            # 原有的其他模式保持不变
            (1, re.compile(r'^第[一二三四五六七八九十]+章\s+')),
            (2, re.compile(r'^第[一二三四五六七八九十]+节\s+')),
            (3, re.compile(r'^第[一二三四五六七八九十]+条\s+')),
            (4, re.compile(r'^第[一二三四五六七八九十]+部分\s+')),
            (5, re.compile(r'^[一二三四五六七八九十]+[、.]')),
            (6, re.compile(r'^[（(][一二三四五六七八九十]+[）)]')),

            # 通用模式 - 匹配任意层级的非零数字 (优先级最高，放在最前面)
            (7, re.compile(r'^[1-9]\d*(\.[1-9]\d*){4,}(\s+)?')),  # 匹配 5层及以上 (如 1.1.1.1.1+)

            # 精确层级匹配
            (8, re.compile(r'^[1-9]\d*\.[1-9]\d*\.[1-9]\d*\.[1-9]\d*(\s+)?')),  # 匹配 4层 (如 1.1.1.1)
            (9, re.compile(r'^[1-9]\d*\.[1-9]\d*\.[1-9]\d*(\s+)?')),  # 匹配 3层 (如 1.1.1)
            (10, re.compile(r'^[1-9]\d*\.[1-9]\d*(\s+)?')),  # 匹配 2层 (如 1.1)
            (11, re.compile(r'^[1-9]\d*(\s+)?')),  # 匹配 1层 (如 1)

            # 其他原有模式
            (12, re.compile(r'^[1-9]\d*[、.](?![、.\d])')),
            (13, re.compile(r'^[1-9]\d*\s')),
            (14, re.compile(r'^[（(][1-9]\d*[）)]')),
            (15, re.compile(r'^[（(][a-z][）)]')),
            (16, re.compile(r'^(I{1,3}|IV|V|VI{0,3}|IX|X)\b')),
            (17, re.compile(r'^[A-Z]\.')),
            (18, re.compile(r'^[a-z]\.')),

            # 百问百答系列
            (19, re.compile(r'^问：'))
        ]

    def split_paragraphs(self, content: str) -> List[str]:
        """
        Split content into paragraphs based on defined separator patterns

        Args:
            content: Input text content

        Returns:
            List of paragraph strings
        """
        lines = content.strip().split('\n')
        paragraphs = []
        current_paragraph = []

        for line in lines:
            line = line.strip()

            # Check if line matches any paragraph separator pattern
            is_separator = any(
                pattern.match(line) for pattern in self.paragraph_patterns
            )

            if is_separator and current_paragraph:
                # Join current paragraph and add to results
                paragraphs.append('\n'.join(current_paragraph))
                current_paragraph = []

            current_paragraph.append(line)

        # Add final paragraph if exists
        if current_paragraph:
            paragraphs.append('\n'.join(current_paragraph))

        return paragraphs

    @staticmethod
    def normalize_text(text: str) -> str:
        """
        Normalize text by replacing Chinese punctuation with English equivalents

        Args:
            text: Input text to normalize

        Returns:
            Normalized text
        """
        replacements = {
            '（': '(',
            '）': ')',
            '、': '.'
        }
        return ''.join(replacements.get(c, c) for c in text)

    def identify_marker_type(self, line: str) -> Optional[int]:
        """
        Identify the marker type of given line

        Args:
            line: Input line to check

        Returns:
            Marker type ID if found, None otherwise
        """
        try:
            normalized_line = self.normalize_text(line.strip())
            for marker_type, pattern in self.marker_patterns:
                if pattern.match(normalized_line):
                    return marker_type
            return None
        except Exception as e:
            self.logger.error(f"Error identifying marker type: {e}")
            return None

    def topu_sort(self, graph: Dict[int, List[int]]) -> Dict[int, int]:
        """
        Calculate the marker_type level with topological sort (Kahn's algorithm)

        Args:
            graph: Dictionary mapping marker type ID to list of child IDs

        Returns:
            Dictionary mapping marker type ID to level

        Raises:
            ValueError: If a cycle is detected in the graph
        """
        markers_level = {}
        topu_sort_queue: List[int] = []
        topu_sort_degree = defaultdict(int)

        try:
            # Calculate in-degrees
            for children in graph.values():
                for v in children:
                    topu_sort_degree[v] += 1

            # Find starting nodes
            for u in graph:
                if topu_sort_degree[u] == 0:
                    topu_sort_queue.append(u)
                    markers_level[u] = 1

            # Process queue
            while topu_sort_queue:
                u = topu_sort_queue.pop(0)
                if u in graph:
                    for v in graph[u]:
                        topu_sort_degree[v] -= 1
                        if topu_sort_degree[v] == 0:
                            markers_level[v] = markers_level[u] + 1
                            topu_sort_queue.append(v)

            # Check for cycles
            if any(topu_sort_degree[u] > 0 for u in graph):
                self.debug_structure_graph(graph)
                raise ValueError("Cycle detected in the graph")

            self.logger.info("Topological sort completed successfully")
            return markers_level

        except Exception as e:
            self.logger.error(f"Error during topological sort: {e}")
            raise

    def build_structure_graph(self, content_lines: List[str]) -> Optional[Dict[int, int]]:
        """
        Build a directed acyclic graph representing the document structure

        Args:
            content_lines: List of text lines from the document

        Returns:
            Dictionary mapping marker type ID to level, or None if build fails
        """
        try:
            graph = {}
            edges: Set[Tuple[int, int]] = set()
            stack: List[int] = []
            in_stack = defaultdict(bool)

            for line_num, current_line in enumerate(content_lines, 1):
                current_line = self.normalize_text(current_line.strip())
                if not current_line:
                    continue

                current_marker_type = self.identify_marker_type(current_line)
                if current_marker_type is None:
                    continue

                if in_stack[current_marker_type]:
                    # Remove markers until we find the current type
                    while stack and stack[-1] != current_marker_type:
                        tail = stack.pop()
                        in_stack[tail] = False
                else:
                    if stack:
                        prev = stack[-1]
                        if prev == current_marker_type:
                            self.logger.warning(
                                f"Duplicate marker type at line {line_num}: {current_line}"
                            )
                            return None

                        stack.append(current_marker_type)
                        in_stack[current_marker_type] = True

                        if (prev, current_marker_type) not in edges:
                            edges.add((prev, current_marker_type))
                            if prev not in graph:
                                graph[prev] = []
                            graph[prev].append(current_marker_type)
                    else:
                        stack.append(current_marker_type)
                        in_stack[current_marker_type] = True
                        # we should add node into graph
                        if current_marker_type not in graph:
                            graph[current_marker_type] = []

            self.logger.info("Graph built successfully")
            return self.topu_sort(graph)

        except Exception as e:
            self.logger.error(f"Error building structure graph: {e}")
            return None

    def parse_file(self, input_source: str, is_file: bool = True) -> Optional[List[ParseResult]]:
        """
        解析文件或文本字符串并构建结构图

        Args:
            input_source: 输入文件路径或文本字符串
            is_file: 标识输入源是否为文件路径，默认为True

        Returns:
            包含段落内容和标记层级的ParseResult列表，解析失败时返回None
        """
        try:
            # 获取内容
            if is_file:
                input_path = Path(input_source)
                if not input_path.exists():
                    raise FileNotFoundError(f"Input file not found: {input_path}")
                with open(input_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            else:
                content = input_source

            # 处理内容
            paragraphs = self.split_paragraphs(content)
            results = []

            for i, paragraph in enumerate(paragraphs, 1):
                try:
                    lines = paragraph.strip().split('\n')
                    marker_levels = self.build_structure_graph(lines)
                    results.append(ParseResult(
                        content=paragraph,
                        marker_levels=marker_levels
                    ))
                except Exception as e:
                    self.logger.error(f"Error parsing paragraph {i}: {e}")
                    results.append(ParseResult(
                        content=paragraph,
                        marker_levels=None,
                        error=str(e)
                    ))

            return results

        except Exception as e:
            self.logger.error(f"Error parsing {'file' if is_file else 'text'}: {e}")
            return None

    def debug_structure_graph(self, graph: Dict[int, List[int]]) -> None:
        """
        Print detailed graph statistics and visualization

        Args:
            graph: Document structure graph where keys are node IDs
                  and values are lists of child node IDs
        """
        try:
            # Get nodes and edges
            nodes = set(graph.keys()).union(
                *[set(children) for children in graph.values()]
            )
            edges = [(node, child) for node, children in graph.items()
                     for child in children]

            # Prepare statistics
            stats = {
                "Nodes": len(nodes),
                "Edges": len(edges),
            }

            # Print formatted output
            self.logger.info("\n" + "=" * 50)
            self.logger.info("Graph Statistics:")
            for key, value in stats.items():
                self.logger.info(f"{key:15}: {value}")

            self.logger.info("\nEdge List:")
            for u, v in sorted(edges):
                self.logger.info(f"{u:3} -> {v:3}")
            self.logger.info("=" * 50)

        except Exception as e:
            self.logger.error(f"Error in debug_structure_graph: {e}")

    def _extract_block_content(self, line: str) -> Tuple[str, str]:
        """
        Extract the block marker and remaining content from a line

        Args:
            line: Input line to process

        Returns:
            Tuple of (block marker, remaining content)
        """
        line = line.strip()
        for _, pattern in self.marker_patterns:
            match = pattern.match(line)
            if match:
                block_end = match.end()
                return line[:block_end].strip(), line[block_end:].strip()
        return "", line

    def parse_to_json_tree(self, content: str) -> Dict[str, Any]:
        """
        Parse content into a JSON-like tree structure

        Args:
            content: Input text content

        Returns:
            Dictionary containing the parsed tree structure
        """
        try:
            # Split into lines and remove empty ones
            lines = [line.strip() for line in content.split('\n') if line.strip()]

            # Get marker levels
            marker_levels = self.build_structure_graph(lines)
            if not marker_levels:
                self.logger.warning("Could not determine marker levels, return original content by default")
                return {
                    "marker_types": [],
                    "output": [{
                        "block": "",
                        "content": "\n".join(lines),
                        "children": []
                    }]
                }

            # Create root node
            root = DocumentNode()
            current_stack = [root]
            current_levels = [0]

            # Track seen marker types for debugging
            seen_marker_types = set()

            for line in lines:
                marker_type = self.identify_marker_type(line)
                if marker_type:
                    seen_marker_types.add(marker_type)

                # * we want all the content in the block, maybe we can use it in the future
                # block, content = self._extract_block_content(line)

                if marker_type is None:
                    # Add content to current node if no marker
                    if current_stack[-1].content:
                        current_stack[-1].content += "\n" + line
                    else:
                        current_stack[-1].content = line
                    continue

                node = DocumentNode(
                    block=line,
                    content="",
                    marker_type=marker_type,
                    level=marker_levels.get(marker_type)
                )

                # Find correct parent based on levels
                while (current_levels and current_stack and
                       marker_levels[marker_type] <= current_levels[-1]):
                    current_stack.pop()
                    current_levels.pop()

                if not current_stack:
                    # todo This should not happen at any time!
                    # because the root node level is 0, smaller than any marker level
                    raise Exception("Unexpected empty stack")

                current_stack[-1].children.append(node)
                current_stack.append(node)
                current_levels.append(marker_levels[marker_type])

            # Create final output structure
            result = {
                "marker_types": sorted(list(seen_marker_types)),
                "output": [{
                    "block": root.block,
                    "content": root.content,
                    "children": self._convert_tree_to_dict(root.children)
                }] if root.content else self._convert_tree_to_dict(root.children)
            }

            return result

        except Exception as e:
            self.logger.error(f"Error parsing to JSON tree: {e}")
            return {"error": str(e)}

    def _convert_tree_to_dict(self, nodes: List[DocumentNode]) -> List[Dict[str, Any]]:
        """
        Convert DocumentNode tree to dictionary format

        Args:
            nodes: List of DocumentNode objects

        Returns:
            List of dictionaries representing the tree structure
        """
        result = []
        for node in nodes:
            node_dict = {
                "block": node.block,
                "content": node.content,
                "children": self._convert_tree_to_dict(node.children),
                "marker_type": node.marker_type
            }
            result.append(node_dict)
        return result

    def parse_file_to_json(self, input_source: str, is_file: bool = True) -> List[Dict[str, Any]]:
        """
        将文件或文本字符串解析为JSON树结构

        Args:
            input_source: 输入文件路径或文本字符串
            is_file: 标识输入源是否为文件路径，默认为True

        Returns:
            包含每个段落解析树结构的字典列表
        """
        try:
            # 获取内容
            if is_file:
                input_path = Path(input_source)
                if not input_path.exists():
                    raise FileNotFoundError(f"Input file not found: {input_path}")
                with open(input_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            else:
                content = input_source

            # 处理内容
            paragraphs = self.split_paragraphs(content)
            results = []

            for paragraph in paragraphs:
                tree = self.parse_to_json_tree(paragraph)
                results.append(tree)

            return results

        except Exception as e:
            self.logger.error(f"Error parsing {'file' if is_file else 'text'} to JSON: {e}")
            return [{"error": str(e)}]

    def _convert_tree_to_list(self, node: Dict, result: List[Dict[str, Any]], parent: str = ""):
        if node.get("block", "") == "" and node.get("content", "") != "":
            result.append({
                "content": parent + "\n" + node.get("content", "") if parent != "" else node.get("content", ""),
                "metadata": {}
            })
            for child in node.get("children", []):
                self._convert_tree_to_list(child, result, parent)
        elif node.get("block", "") != "" and node.get("content", "") == "":
            if node.get("marker_type", -1) in [1, 2, 4, 5]:
                parent = parent + "\n" + node.get("block", "") if parent != "" else node.get("block", "")
            elif node.get("marker_type", -1) in [3]:
                if not node.get("children", []):
                    result.append({
                        "content": parent + "\n" + node.get("block", "") if parent != "" else node.get("block", ""),
                        "metadata": {}
                    })
                else:
                    parent = parent + "\n" + node.get("block", "") if parent != "" else node.get("block", "")
            else:
                result.append({
                    "content": parent + "\n" + node.get("block", "") if parent != "" else node.get("block", ""),
                    "metadata": {}
                })
            for child in node.get("children", []):
                self._convert_tree_to_list(child, result, parent)

    def parse_file_to_list(self, input_source: str, is_file: bool = True) -> List[Dict[str, Any]]:
        """
        将文件或文本字符串解析为JSON树结构

        Args:
            input_source: 输入文件路径或文本字符串
            is_file: 标识输入源是否为文件路径，默认为True

        Returns:
            包含每个段落解析树结构的字典列表
        """
        try:
            # 获取内容
            if is_file:
                input_path = Path(input_source)
                if not input_path.exists():
                    raise FileNotFoundError(f"Input file not found: {input_path}")
                with open(input_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            else:
                content = input_source

            # 处理内容
            paragraphs = self.split_paragraphs(content)
            trees = []

            for paragraph in paragraphs:
                tree = self.parse_to_json_tree(paragraph)
                trees.append(tree)

            results = []
            for tree in trees:
                for node in tree["output"]:
                    self._convert_tree_to_list(node, results, "")
            return results

        except Exception as e:
            self.logger.error(f"Error parsing {'file' if is_file else 'text'} to JSON: {e}")
            return [{"error": str(e)}]

    def is_chinese_law(self, content: str):
        pattern = r'第[一二三四五六七八九十]+章\s+'
        matches = re.findall(pattern, content, re.DOTALL)
        if len(matches) > 3:
            return True
        return False


class FDADocumentStructureParser(DocumentStructureParser):

    def _compile_marker_patterns(self) -> None:
        """Compile regex patterns for FDA document section markers"""
        # fda documents like space after marker
        self.marker_patterns = [
            # Combined pattern for Roman numerals and special sections
            (1, re.compile(r'^(?:(?:I{1,3}|IV|V|VI{1,3}|VII{1,3}|VIII{1,3}|IX|X)\. |(APPENDIX|REFERENCES))')),

            # Capital letters with dot and space(e.g., "A. ", "B. ")
            (2, re.compile(r'^[A-Z]\. ')),

            # Numbers with dot and space(e.g., "1.", "2.")
            (3, re.compile(r'^[1-9]\d*\. ')),

            # Lowercase letters with dot and space(e.g., "a.", "b.")
            (4, re.compile(r'^[a-z]\. ')),

            # Nested number patterns (e.g., "1.1", "1.2.3")
            (5, re.compile(r'^(?:[1-9]\d*\.)+[1-9]\d* ')),

            # Parenthetical patterns
            (6, re.compile(r'^\(\d+\) ')),  # (1), (2)
            (7, re.compile(r'^\([a-z]\) '))  # (a), (b)
        ]


class ICHDocumentStructureParser(DocumentStructureParser):

    def _compile_marker_patterns(self) -> None:
        """Compile regex patterns for FDA document section markers"""
        # ICH documents like space after marker
        self.marker_patterns = [
            # Combined pattern for Roman numerals and special sections
            (1, re.compile(r'^(?:(?:I{1,3}|IV|V|VI{1,3}|VII{1,3}|VIII{1,3}|IX|X)\. |(APPENDIX|REFERENCES))')),

            # Capital letters with dot and space(e.g., "A. ", "B. ")
            (2, re.compile(r'^[A-Z]\. ')),

            # Numbers with dot and space(e.g., "1.", "2.") - modified to non-zero
            (3, re.compile(r'^[1-9]\d*\. ')),

            # Lowercase letters with dot and space(e.g., "a.", "b.")
            (4, re.compile(r'^[a-z]\. ')),

            # 通用模式 - 匹配任意层级的非零数字 (优先级最高，放在最前面)
            (5, re.compile(r'^[1-9]\d*(\.[1-9]\d*){4,} ')),  # 匹配 5层及以上 (如 1.1.1.1.1+)

            # 精确层级匹配
            (6, re.compile(r'^[1-9]\d*\.[1-9]\d*\.[1-9]\d*\.[1-9]\d* ')),  # 匹配 4层 (如 1.1.1.1)
            (7, re.compile(r'^[1-9]\d*\.[1-9]\d*\.[1-9]\d* ')),  # 匹配 3层 (如 1.1.1)
            (8, re.compile(r'^[1-9]\d*\.[1-9]\d* ')),  # 匹配 2层 (如 1.1)

            # Parenthetical patterns
            (9, re.compile(r'^\([1-9]\d*\) ')),  # (1), (2)
            (10, re.compile(r'^\([a-z]\) ')),  # (a), (b)
        ]
