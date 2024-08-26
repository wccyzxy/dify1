import json

from core.tools.entities.tool_entities import ToolInvokeMessage
from core.tools.tool.builtin_tool import BuiltinTool
from core.tools.provider.builtin.huanyu_docx.utils.docx_utils import doc_to_json, extract_text_from_docx
from core.tools.provider.builtin.huanyu_docx.utils.ac_utils import AcAutomation
from core.tools.provider.builtin.huanyu_xlsx.utils.xlsx_utils import read_xlsx, convert_to_json
import os


class ExtractSuolueyu(BuiltinTool):
    def _invoke(self, user_id: str, tool_parameters: dict) -> ToolInvokeMessage | list[ToolInvokeMessage]:
        file_source_id = tool_parameters.get("file_source_id", '')
        if not file_source_id:
            raise Exception("请传入文件source id")
        file_path_list = self.find_files_by_id(file_source_id)
        if len(file_path_list) == 0:
            raise Exception("未找到文件")

        file_path = file_path_list[0]
        if not file_path.endswith(".docx"):
            raise Exception("传入文件不是docx文件")

        xlsx_file_source_id = tool_parameters.get("xlsx_source_id", '')
        if not xlsx_file_source_id:
            raise Exception("请传入文件xlsx source id")
        xlsx_file_path_list = self.find_files_by_id(xlsx_file_source_id)
        if len(xlsx_file_path_list) == 0:
            raise Exception("xlsx未找到文件")

        xlsx_file_path = xlsx_file_path_list[0]
        if not xlsx_file_path.endswith(".xlsx"):
            raise Exception("传入文件不是xlsx文件")

        sheet_name = '汇总'
        df = read_xlsx(xlsx_file_path, sheet_name)
        suolueyu_json = convert_to_json(df)
        if suolueyu_json == {}:
            raise Exception("请传入suolueyu_json")
        ac = AcAutomation()
        suo_lue_yu = suolueyu_json
        content = extract_text_from_docx(file_path)
        matches = self.find_all_matches(ac, suo_lue_yu, content)
        result = {}
        for match in matches:
            value = suo_lue_yu[match[1]]
            if match[1] in result:
                continue
            result[match[1]] = {'sentence': match[2], 'value': value}
        return self.create_json_message(result)

    def find_all_matches(self, ac, suo_lue_yu, text):
        matches = ac.find_matches(text, suo_lue_yu.keys())
        return matches

    def find_files_by_id(self, id):
        # 获取当前工作目录
        current_dir = os.getcwd()
        # 指定要搜索的文件夹
        data_folder = os.path.join(current_dir, 'storage', 'upload_files')

        # 初始化结果列表
        result = []

        # 遍历文件夹及其子目录
        for root, dirs, files in os.walk(data_folder):
            for file in files:
                # 分割文件名和扩展名
                name, extension = os.path.splitext(file)
                # 如果文件名部分与ID匹配
                if name == str(id):
                    # 构建相对路径
                    relative_path = os.path.relpath(os.path.join(root, file), current_dir)
                    # 添加到结果列表
                    result.append(relative_path)

        return result