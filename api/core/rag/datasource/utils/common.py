def parse_extraction_query(query: str) -> dict:
    """
    解析提取类查询
    
    支持两种格式:
    1. '从文件xxx中提取xxxx'
    2. '从文件xxx的xxx中提取xxxx' 
    
    Returns:
        dict: {
            'filename': 文件名,
            'title': 内容标题(如果没有则为None),
            'query': 提取内容
        }
    """
    result = {
        'filename': None,
        'title': None, 
        'query': None
    }
    if not query:
        return result
    
    # 检查是否符合基本格式
    if not query.startswith('从文件') or '中提取' not in query:
        return result
        
    # 分割查询字符串
    file_part = query.split('中提取')[0][3:]  # 去掉"从文件"
    query_part = query.split('中提取')[1]
    
    # 处理文件名和标题
    if '的' in file_part:
        filename, title = file_part.split('的', 1)
        result['filename'] = filename.strip()
        result['title'] = title.strip()
    else:
        result['filename'] = file_part.strip()
        
    result['query'] = query_part.strip()
    
    return result