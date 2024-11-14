import json
import re

from docx import Document
from lxml import etree
from openpyxl.workbook import Workbook


class DocxUtils:
    def __init__(self, chunk_size):
        self.doc = None
        self.chunk_size = chunk_size

    def doc_to_json(self, doc_path):
        # 加载Word文档
        doc = Document(doc_path)

        full_text = []

        body = doc.element.body

        # 遍历body元素中的所有子元素
        for element in body:
            if element.tag.endswith('p'):  # Check if it's a paragraph
                # 提取段落文本
                para_text = element.text
                if para_text:
                    # 检查段落样式
                    style_name = ''
                    try:
                        style_name = doc.styles.element.style_lst[int(element.style)].name_val if element.style else ''
                    except Exception as e:
                        style_name = ''
                    if style_name == 'heading 1':
                        full_text.append({'content': para_text, 'type': 'text', 'level': 1})
                    elif style_name == 'heading 2':
                        full_text.append({'content': para_text, 'type': 'text', 'level': 2})
                    elif style_name == 'heading 3':
                        full_text.append({'content': para_text, 'type': 'text', 'level': 3})
                    elif style_name == 'heading 4':
                        full_text.append({'content': para_text, 'type': 'text', 'level': 4})
                    elif style_name == 'heading 5':
                        full_text.append({'content': para_text, 'type': 'text', 'level': 5})
                    else:
                        full_text.append({'content': para_text, 'type': 'text', 'level': -1})
            elif element.tag.endswith('tbl'):  # Check if it's a table
                # 提取表格数据
                table_data = []
                for row in element.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tr'):
                    row_data = []
                    for cell in row.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tc'):
                        texts = cell.xpath(
                            'descendant::w:t[not(ancestor::w:commentRangeStart) and not(ancestor::w:commentRangeEnd)]')
                        cell_text = "".join([node.text.strip() if node.text else "" for node in texts])
                        row_data.append(cell_text)
                    table_data.append(row_data)
                full_text.append({'content': table_data, 'type': 'table', 'level': -1})

        full_text

    def doc_to_json_with_level(self, doc_path):
        # 加载Word文档
        doc = Document(doc_path)

        doc_json = {
            'type': 'document',
            'level': -1,
            'content': '',
            'children': []
        }

        section_stack = [doc_json]
        table_title = ''

        body = doc.element.body

        # 遍历body元素中的所有子元素
        for element in body:
            if element.tag.endswith('p'):  # Check if it's a paragraph
                # 提取段落文本
                para_text = element.text
                if para_text:
                    # 检查段落样式
                    style_name = ''
                    try:
                        style_name = doc.styles.element.style_lst[int(element.style)].name_val if element.style else ''
                    except Exception as e:
                        style_name = ''
                    level = -1
                    if style_name == 'heading 1':
                        level = 1
                    elif style_name == 'heading 2':
                        level = 2
                    elif style_name == 'heading 3':
                        level = 3
                    elif style_name == 'heading 4':
                        level = 4
                    elif style_name == 'heading 5':
                        level = 5
                    elif style_name == 'heading 6':
                        level = 6
                    if level > 0:
                        # 创建一个新的section
                        new_section = {
                            'type': 'text',
                            'level': level,
                            'content': para_text,
                            'children': []
                        }
                        # 如果新层级小于等于栈顶元素的层级，则弹出栈顶元素直到找到合适的层级
                        while section_stack and section_stack[-1]['level'] and level <= section_stack[-1]['level']:
                            section_stack.pop()

                        # 将新节点添加到当前层级的末尾
                        section_stack[-1]['children'].append(new_section)
                        section_stack.append(new_section)
                    else:
                        if para_text.startswith('表 '):
                            table_title = para_text
                        else:
                            current_section = section_stack[-1]
                            current_section['children'].append({
                                'type': 'text',
                                'level': -1,
                                'content': para_text
                            })
            elif element.tag.endswith('tbl'):  # Check if it's a table
                # 提取表格数据
                table_data = []
                for row in element.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tr'):
                    row_data = []
                    for cell in row.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tc'):
                        texts = cell.xpath(
                            'descendant::w:t[not(ancestor::w:commentRangeStart) and not(ancestor::w:commentRangeEnd)]')
                        cell_text = "".join([node.text.strip() if node.text else "" for node in texts])
                        row_data.append(cell_text)
                    table_data.append(row_data)
                current_section = section_stack[-1]
                current_section['children'].append({
                    'type': 'table',
                    'title': table_title,
                    'content': table_data,
                    'level': -1
                })
                table_title = ''

        return doc_json

    def extract_paragraph_content(self, paragraph):
        content = []
        for run in paragraph.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}r'):
            text = "".join(
                [t.text for t in run.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t')])
            if text:
                content.append(text)
        content = "".join(content)

        # 处理公式
        oMath = paragraph.find('.//{http://schemas.openxmlformats.org/officeDocument/2006/math}oMath')
        if oMath is not None:
            markdown_equation = self.omml_to_markdown(oMath)
            content = f"{markdown_equation} {content}"

        return content

    def omml_to_markdown(self, omath):
        # 将OMML转换为简单的Markdown公式
        equation = etree.tostring(omath, encoding='unicode')
        equation = self.handle_special_characters(equation)
        # 替换一些常见的OMML标签为Markdown语法
        equation = re.sub(r'<m:oMath.*?>(.*?)</m:oMath>', r'$\1$', equation, flags=re.DOTALL)
        equation = re.sub(r'<m:f>(.*?)</m:f>', r'\\frac{\1}', equation, flags=re.DOTALL)
        equation = re.sub(r'<m:num>(.*?)</m:num>', r'{\1}', equation, flags=re.DOTALL)
        equation = re.sub(r'<m:den>(.*?)</m:den>', r'{\1}', equation, flags=re.DOTALL)
        equation = re.sub(r'<m:sup>(.*?)</m:sup>', r'^{\1}', equation, flags=re.DOTALL)
        equation = re.sub(r'<m:sub>(.*?)</m:sub>', r'_{\1}', equation, flags=re.DOTALL)
        equation = re.sub(r'<m:r>(.*?)</m:r>', r'\1', equation, flags=re.DOTALL)
        equation = re.sub(r'<m:t>(.*?)</m:t>', r'\1', equation, flags=re.DOTALL)

        # 移除所有剩余的XML标签
        equation = re.sub(r'<.*?>', '', equation)

        # 清理空白字符
        equation = re.sub(r'\s+', ' ', equation).strip()

        return equation

    @staticmethod
    def handle_special_characters(equation):
        # 定义特殊字符映射
        symbol_map = {
            'F065': '\\Alpha',  # 大写 Alpha
            'F066': '\\Beta',  # 大写 Beta
            'F067': '\\Chi',  # 大写 Chi
            # ... 添加更多映射
        }

        # 使用正则表达式查找并替换特殊字符
        def replace_symbol(match):
            char_code = match.group(1)
            return symbol_map.get(char_code, f'\\symbol{{{char_code}}}')

        equation = re.sub(r'<w:sym\s+w:font="Symbol"\s+w:char="(F[0-9A-F]{3})"/>', replace_symbol, equation)

        return equation

    def doc_to_json_with_level_v1(self, doc_path):
        # 加载Word文档
        doc = Document(doc_path)

        doc_json = {
            'type': 'document',
            'level': -1,
            'content': '',
            'children': []
        }

        section_stack = [doc_json]
        table_title = ''

        body = doc.element.body

        # 遍历body元素中的所有子元素
        heading_pattern = re.compile(r'^(\d+(\.\d+)*[.)]?)')
        for element in body:
            if element.tag.endswith('p'):  # Check if it's a paragraph
                # 提取段落文本
                para_text = self.extract_paragraph_content(element)

                # 去掉目录
                if para_text.replace(' ', '') == "目录":
                    continue
                if element.style and element.style.startswith("TOC"):
                    continue

                if para_text:
                    style_name = ''
                    try:
                        style_name = doc.styles.element.style_lst[int(element.style)].name_val if element.style else ''
                    except Exception as e:
                        style_name = ''
                    level = -1
                    if style_name == 'heading 1':
                        level = 1
                    elif style_name == 'heading 2':
                        level = 2
                    elif style_name == 'heading 3':
                        level = 3
                    elif style_name == 'heading 4':
                        level = 4
                    elif style_name == 'heading 5':
                        level = 5
                    elif style_name == 'heading 6':
                        level = 6
                    else:
                        match = heading_pattern.match(para_text)
                        if match:
                            # 计算标题序号中的点的数量来确定标题的层级
                            level = len(match.group(1).split('.'))
                            # 如果层级大于3，则从第4级开始依次增加
                            if level > 3:
                                level += 6
                    if level > 0:
                        # 创建一个新的section
                        new_section = {
                            'type': 'text',
                            'level': level,
                            'content': para_text,
                            'children': []
                        }
                        # 如果新层级小于等于栈顶元素的层级，则弹出栈顶元素直到找到合适的层级
                        while section_stack and section_stack[-1]['level'] and level <= section_stack[-1]['level']:
                            section_stack.pop()

                        # 将新节点添加到当前层级的末尾
                        section_stack[-1]['children'].append(new_section)
                        section_stack.append(new_section)
                    else:
                        if para_text.startswith('表 ') or para_text.endswith('表'):
                            table_title = para_text
                        else:
                            current_section = section_stack[-1]
                            current_section['children'].append({
                                'type': 'text',
                                'level': -1,
                                'content': para_text
                            })
            elif element.tag.endswith('tbl'):  # Check if it's a table
                # 提取表格数据
                table_data = []
                for row in element.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tr'):
                    row_data = []
                    for cell in row.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tc'):
                        texts = cell.xpath(
                            'descendant::w:t[not(ancestor::w:commentRangeStart) and not(ancestor::w:commentRangeEnd)]')
                        cell_text = "".join([node.text.strip() if node.text else "" for node in texts])
                        row_data.append(cell_text)
                    table_data.append(row_data)
                current_section = section_stack[-1]
                current_section['children'].append({
                    'type': 'table',
                    'title': table_title,
                    'content': table_data,
                    'level': -1
                })
                table_title = ''

        return doc_json

    @staticmethod
    def clean_string(s):
        # 将中文空格替换为英文空格
        s = s.replace('\u3000', ' ')
        # 去除前后的空白字符
        s = s.strip()
        # 使用正则表达式替换连续的空格为单个空格
        s = re.sub(r'\s+', ' ', s)
        return s

    def split_by_title(self, content, result, parent_titles=[]):
        if content['type'] == 'table':
            title = self.clean_string(content['title']) + "\n"
            text = []
            for row in content['content']:
                row_text = self.clean_string('|'.join(row)) + "\n"
                if len(text) == 0:
                    text.append(title + row_text)
                else:
                    if len(text[-1]) + len(row_text) > self.chunk_size:
                        text.append(title + row_text)
                    else:
                        text[-1] += row_text
        else:
            text = self.clean_string(content['content'])

        # 根据当前内容的级别，决定使用哪些父级标题
        current_level = content['level']
        relevant_parents = [title for title, level in parent_titles if level < current_level]

        # 添加父级标题
        full_title = ' '.join(relevant_parents + [text]) if current_level > 0 else text

        if content['level'] > 0:
            if result[-1] in full_title:
                result[-1] = full_title
            else:
                result.append(full_title)
        elif content['type'] == 'table':
            if isinstance(full_title, str):
                result.append(full_title)
            elif isinstance(full_title, list):
                for item in full_title:
                    result.append(item)
            else:
                print("Invalid type of full_title:", type(full_title))
        else:
            result[-1] = result[-1] + text + '\n'
        if 'children' in content.keys():
            new_parent_titles = parent_titles + [(text, current_level)] if current_level > 0 else parent_titles
            for child in content['children']:
                result = self.split_by_title(child, result, new_parent_titles)

        return result

    @staticmethod
    def write_to_excel(data_list, output_path):
        # 创建一个新的工作簿
        wb = Workbook()

        # 激活默认的工作表
        ws = wb.active

        # 设置表头
        ws.append(['Content'])

        # 遍历列表并将每个元素添加到新的一行
        for content in data_list:
            ws.append([content])

        # 保存工作簿到文件
        wb.save(output_path)

    def extract_to_xlsx(self, doc_path, output_path=''):
        content_json = self.doc_to_json_with_level_v1(doc_path)
        result = self.split_by_title(content_json, [''])
        if len(result) > 0:
            output_path = doc_path.replace('.docx', '.xlsx') if output_path == '' else output_path
            self.write_to_excel(result, output_path)

    def extract_to_list(self, doc_path):
        content_json = self.doc_to_json_with_level_v1(doc_path)
        result = self.split_by_title(content_json, [''])
        return result


if __name__ == '__main__':
    # doc_path = 'data/医学监查计划正文模板.docx'
    # doc_table_path = 'data/test_deal_by_suolueyu.docx'
    # doc_json = doc_to_json_with_level(doc_path)
    # with open('data/doc_json1.json', 'w') as f:http://10.10.201.35:8888/RD/cube-engine/-/commit/47e747aa219053afdf22f2c887e81fbe24d96b1a
    #     json.dump(doc_json, f, indent=4)
    # print(json.dumps({"key": "医学监查计划"}))
    doc_util = DocxUtils(chunk_size=1000)
    doc_util.extract_to_xlsx('data/方案.docx')
