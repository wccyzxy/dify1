from core.tools.entities.tool_entities import ToolInvokeMessage
from core.tools.tool.builtin_tool import BuiltinTool
from core.tools.provider.builtin.huanyu_docx.utils.docx_utils import doc_to_json, save_content_to_md
import os


class DocxToMarkdown(BuiltinTool):
    def _invoke(self, user_id: str, tool_parameters: dict) -> ToolInvokeMessage | list[ToolInvokeMessage]:
        file_source_id = tool_parameters.get("file_source_id", '')
        if not file_source_id:
            return ToolInvokeMessage(message="�봫���ļ�source id", type="error")
        file_path_list = self.find_files_by_id(file_source_id)
        if len(file_path_list) == 0:
            return ToolInvokeMessage(message="δ�ҵ��ļ�", type="error")

        file_path = file_path_list[0]
        if not file_path.endswith(".docx"):
            return ToolInvokeMessage(message="�����ļ�����docx�ļ�", type="error")

        content_list = doc_to_json(file_path)
        return save_content_to_md(content_list)


    def find_files_by_id(self, id):
        # ��ȡ��ǰ����Ŀ¼
        current_dir = os.getcwd()
        # ָ��Ҫ�������ļ���
        data_folder = os.path.join(current_dir, 'data')

        # ��ʼ������б�
        result = []

        # �����ļ��м�����Ŀ¼
        for root, dirs, files in os.walk(data_folder):
            for file in files:
                # �ָ��ļ�������չ��
                name, extension = os.path.splitext(file)
                # ����ļ���������IDƥ��
                if name == str(id):
                    # �������·��
                    relative_path = os.path.relpath(os.path.join(root, file), current_dir)
                    # ��ӵ�����б�
                    result.append(relative_path)

        return result