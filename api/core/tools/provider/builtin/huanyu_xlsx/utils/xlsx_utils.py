import pandas as pd
import re


# ��ȡxlsx�ļ�
def read_xlsx(file_path, sheet_name='Sheet1'):
    return pd.read_excel(file_path, sheet_name=sheet_name)


# �����ַ���
def clean_string(s):
    if pd.isna(s):
        return ""
    # �����Ŀո��滻ΪӢ�Ŀո�
    s = s.replace('\u3000', ' ')
    # ȥ��ǰ��Ŀհ��ַ�
    s = s.strip()
    # ʹ��������ʽ�滻�����Ŀո�Ϊ�����ո�
    s = re.sub(r'\s+', ' ', s)
    return s


# ������ת��ΪJSON��ʽ
def convert_to_json(df):
    result = {}
    for _, row in df.iterrows():
        obj = {
            "���": clean_string(str(row["���"])),
            "������": clean_string(row["������"]),
            "Ӣ��ȫ��": clean_string(row["Ӣ��ȫ��"]),
            "����ȫ��": clean_string(row["����ȫ��"])
        }
        # ʹ��������Ӣ��ȫ����Ϊ��
        key = clean_string(row["������"])
        if key:  # ֻ�е�����Ϊ��ʱ�����
            if key in result:
                result[key].append(obj)
            else:
                result[key] = [obj]
    return result


def extract_suolueyu_json_from_xlsx(input_file, sheet_name='Sheet1'):
    sheet_name = '����'
    df = read_xlsx(input_file, sheet_name)
    json_data = convert_to_json(df)
    return json_data


if __name__ == "__main__":
    input_file = 'AI�������20240718.xlsx'  # �滻Ϊ���������ļ���
    output_file = 'AI�������20240718.json'  # ����ļ���
    sheet_name = '����'  # �滻Ϊ���Ĺ���������
    extract_suolueyu_json_from_xlsx(input_file, sheet_name)
