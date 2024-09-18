import pandas as pd
import re


# 读取xlsx文件
def read_xlsx(file_path, sheet_name='Sheet1'):
    return pd.read_excel(file_path, sheet_name=sheet_name, engine='openpyxl')


# 清理字符串
def clean_string(s):
    if pd.isna(s):
        return ""
    # 将中文空格替换为英文空格
    s = s.replace('\u3000', ' ')
    # 去除前后的空白字符
    s = s.strip()
    # 使用正则表达式替换连续的空格为单个空格
    s = re.sub(r'\s+', ' ', s)
    return s


# 将数据转换为JSON格式
def convert_to_json(df):
    result = {}
    for _, row in df.iterrows():
        obj = {
            "num": clean_string(str(row["序号"])),
            "short": clean_string(row["缩略语"]),
            "all_en": clean_string(row["英文全称"]),
            "all_zh": clean_string(row["中文全称"])
        }
        # 使用清理后的英文全称作为键
        key = clean_string(row["缩略语"])
        if key:  # 只有当键不为空时才添加
            if key in result:
                result[key].append(obj)
            else:
                result[key] = [obj]
    return result


def extract_suolueyu_json_from_xlsx(input_file, sheet_name='Sheet1'):
    sheet_name = '汇总'
    df = read_xlsx(input_file, sheet_name)
    json_data = convert_to_json(df)
    return json_data


if __name__ == "__main__":
    input_file = 'AI缩略语库20240718.xlsx'  # 替换为您的输入文件名
    output_file = 'AI缩略语库20240718.json'  # 输出文件名
    sheet_name = '汇总'  # 替换为您的工作表名称
    extract_suolueyu_json_from_xlsx(input_file, sheet_name)
