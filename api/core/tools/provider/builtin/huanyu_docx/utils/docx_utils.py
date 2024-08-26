from docx import Document
from copy import deepcopy


def doc_to_json(doc_path):
    # 加载Word文档
    doc = Document(doc_path)

    full_text = []

    body = doc.element.body
    table_title = ''

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
                    if para_text.startswith('表') or para_text.startswith('附表'):
                        table_title = para_text
                    else:
                        full_text.append({'content': para_text, 'type': 'text', 'level': -1})
        elif element.tag.endswith('tbl'):  # Check if it's a table
            # 提取表格数据
            table_data = []
            for row in element.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tr'):
                row_data = []
                for cell in row.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tc'):
                    texts = cell.xpath('descendant::text()')
                    cell_text = "".join([node.strip() for node in texts])
                    row_data.append(cell_text)
                table_data.append(row_data)
            full_text.append({'content': table_data, 'title': table_title, 'type': 'table', 'level': -1})

    return full_text


def doc_to_json_with_level(doc_path):
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
                    if para_text.startswith('表'):
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
                    texts = cell.xpath('descendant::text()')
                    cell_text = "".join([node.strip() for node in texts])
                    row_data.append(cell_text)
                table_data.append(row_data)
            current_section = section_stack[-1]
            current_section['children'].append({
                'type': 'table',
                'title': table_title,
                'content': table_data,
                'level': -1
            })

    return doc_json


def save_content_to_md(content_list):
    content = ''
    for item in content_list:
        if item['type'] == 'text' and item['level'] > 0:
            content += '#' * item['level'] + ' ' + item['content'] + '\n\n'
        elif item['type'] == 'table':
            content += f"**Table Title:** {item.get('title', 'No Title')}\n\n"
            for row in item['content']:
                content += '|'.join(row) + '\n'
            content += '\n\n'
        elif item['type'] == 'text':
            content += item['content'] + '\n\n'
    return content


def copy_table_after(table, paragraph):
    tbl, p = table._tbl, paragraph._p
    new_tbl = deepcopy(tbl)
    p.addnext(new_tbl)


def move_table_after(table, paragraph):
    tbl, p = table._tbl, paragraph._p
    p.addnext(tbl)


def move_paragraph_after(paragraph, paragraph_after):
    p, p_after = paragraph._p, paragraph_after._p
    p_after.addnext(p)


def delete_table_with_title(document, expect_text):
    allTables = document.tables
    for activeTable in allTables:
        if activeTable.cell(0, 0).paragraphs[0].text == expect_text:
            activeTable._element.getparent().remove(activeTable._element)


def extract_tables_from_docx(file_path):
    # 打开文档
    doc = Document(file_path)

    result = ""
    # 遍历文档中的所有表格
    for i, table in enumerate(doc.tables):
        result += f"Table {i + 1}:\n"
        for row in table.rows:
            row_data = []
            for cell in row.cells:
                row_data.append(cell.text)
            result += " | ".join(row_data) + "\n"
        result += "\n"

    return result


def extract_paragraphs_from_docx(file_path):
    # 打开docx文件
    doc = Document(file_path)

    # 初始化一个空字符串来存储文本
    full_text = []

    # 遍历文档中的所有段落
    for para in doc.paragraphs:
        full_text.append(para.text)

    # 将所有段落的文本连接成一个字符串
    return '\n'.join(full_text)


def extract_text_from_docx(file_path):
    # 打开docx文件
    doc = Document(file_path)

    # 初始化一个空列表来存储文本
    full_text = []

    # 遍历文档中的所有段落
    for para in doc.paragraphs:
        text = para.text.strip()  # 去除段落文本的前后空白
        if text:  # 如果段落文本不为空，则添加到列表中
            full_text.append(text)

    # 遍历文档中的所有表格
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    text = para.text.strip()  # 去除段落文本的前后空白
                    if text:  # 如果段落文本不为空，则添加到列表中
                        full_text.append(text)

    # 将所有段落和表格的文本连接成一个字符串
    return '\n'.join(full_text)
