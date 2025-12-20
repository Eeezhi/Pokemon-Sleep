"""
OCR文字识别修正规则
用于修正EasyOCR识别中常见的错误
"""
import re


def correct_ocr_text(text: str) -> str:
    """
    应用所有OCR修正规则到文本
    
    Args:
        text: 原始OCR识别的文本
        
    Returns:
        修正后的文本
    """
    if not text or not isinstance(text, str):
        return text
    
    text = text.strip()
    
    # ========== 第一步：处理包含特殊模式的regex（必须在字符替换之前）==========
    text = re.sub(r'\[\+\.\s*', 'Lv.', text)  # [+. → Lv.
    text = re.sub(r'\[\+\.', 'Lv.', text)  # [+. → Lv. (无空格版本)
    text = re.sub(r'匕\+\.\s*', 'Lv.', text)  # 匕+. → Lv.
    text = re.sub(r'\[\.\.?', 'Lv.', text)  # [. 或 [.. → Lv.
    text = re.sub(r'\$\?\s*', 'Lv.', text)  # $? → Lv.
    text = re.sub(r'\$\[\s*', 'Lv.', text)  # $[ → Lv.
    
    # ========== 第二步：符号和字符替换 ==========
    text = text.replace('$', 'S')  # $ → S
    text = text.replace('|', 'S')  # | → S
    text = text.replace('兔', 'M')  # 兔 → M
    text = text.replace('舊', 'S')  # 舊 → S (技能等级)
    text = text.replace('?', 'E')  # ? → E
    text = text.replace('冑', 'M')  # 冑 → M
    text = text.replace(';', ',')  # ; → ，
    text = text.replace('臺', 'M')  # 癲 → 夢
    
    # 中文字修正
    text = text.replace('芎', '夢')  # 癲 → 癒
    text = text.replace('瘋', '癒')  # 瘋 → 癒
    text = text.replace('癥', '癒')  # 癥 → 癒
    text = text.replace('青', '害')  # 青 → 害
    text = text.replace('盜', '持')  # 盜 → 持
    text = text.replace('複', '復')  # 複 → 復
    text = text.replace('凶', 'M')  # 凶 → M
    text = text.replace('日', 'M')  # 日 → M
    text = text.replace('氏', 'E')  # 氏 → E (睡眠EXP)
    text = text.replace('巨人', 'EXP')  # 巨人 → EXP
    #text = text.replace('才怪', '')  # 才怪 → 空（去除OCR噪音）
    # 注意：不要随意转换可能是宝可梦名字的字
    text = text.replace('齧', '喵')  # 可能是宝可梦名字的一部分
    # text = text.replace('葉', '叶')  # 葉字在宝可梦名字中很常见
    text = text.replace('亡', '')  # 亡 → 空（OCR噪音）
    text = text.replace("'", '')  # 单引号 → 空
    
    # ========== 第三步：更多regex清理 ==========
    text = re.sub(r'\+\.\s*', 'Lv.', text)  # +. → Lv.
    text = re.sub(r'<\d+', '', text)  # <2, <5 → 空
    text = re.sub(r'\*\d+', '', text)  # *2 → 空
    text = re.sub(r'\d+_\d+', '', text)  # 115_1 → 空（无意义数字组合）
    
    # 修正「樹果」附近的符号
    if '樹果' in text:
        text = re.sub(r'[^\u4e00-\u9fa5]+樹果', '樹果', text)  # 保留中文+樹果
    
    # 清理开头的无效字符
    text = re.sub(r'^[^\u4e00-\u9fa5A-Za-z0-9]+', '', text)
    
    # 技能等级中单独的[ → M
    text = re.sub(r'提升\[', '提升M', text)
    text = re.sub(r'上限\[', '上限M', text)
    
    # ========== 修正技能等级后缀（S/M/L）==========
    # 数字 5 → S
    if '速度5' in text or '提升5' in text or '上限5' in text:
        text = text.replace('速度5', '速度S').replace('提升5', '提升S').replace('上限5', '上限S')
    
    # ========== 修正睡眠EXP相关错误 ==========
    if '睡眠E' in text and 'XP' not in text:
        text = text.replace('睡眠E', '睡眠EXP')
    if 'EXP獲得量' in text:
        text = text.replace('EXP獲得量', 'EXP獎勵')
    
    # ========== 技能名称中的 1 → M（只在特定上下文中替换）==========
    if '提升1' in text or '提升l' in text:
        text = text.replace('提升1', '提升M').replace('提升l', '提升M')
    if '上限1' in text or '上限l' in text:
        text = text.replace('上限1', '上限M').replace('上限l', '上限M')
    
    return text


def remove_english(text: str) -> str:
    """移除文本中的英文字符"""
    return re.sub(r'[A-Za-z]', '', text)


def extract_pokemon_name(text: str) -> str:
    """
    从包含等级信息的文本中提取宝可梦名字
    例如：'Lv.10新葉喵' → '新葉喵'
    
    Args:
        text: 可能包含等级前缀的文本
        
    Returns:
        提取出的宝可梦名字
    """
    # 移除 Lv.数字 前缀
    text = re.sub(r'^Lv\.\d+', '', text)
    return text.strip()
