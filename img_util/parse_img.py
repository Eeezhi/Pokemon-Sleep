import re
from datetime import datetime
import streamlit as st
#from pymongo.mongo_client import MongoClient
import warnings; warnings.filterwarnings('ignore')
import requests
import os
import pandas as pd
import cv2
import numpy as np
from io import BytesIO

raw_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "dbdata")

# Connect MongoDB to get possible item lists
# def connect_mongodb():
#     username = st.secrets["db_username"]
#     password = st.secrets["db_password"]
#     uri = f"mongodb+srv://{username}:{password}@cluster0.dhzzdc6.mongodb.net/?retryWrites=true&w=majority"
#     client = MongoClient(uri)
#     db_conn = client['PokemonSleep']
#     return db_conn

# def get_db_item_list(db_conn, target_collection):
#     collection = db_conn[target_collection]
#     item_all = collection.find({})
#     item_list = list(set([i['_airbyte_data']['_id'] for i in item_all]))
#     item_list.insert(0, '---')
#     return item_list

def get_db_item_list(collection_name: str):
    """
    模拟从 MongoDB 获取集合数据，改为从 /data/dbdata 下的 CSV 文件读取。
    """
    file_path = os.path.join(raw_DATA_DIR, f"{collection_name}.csv")
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"找不到文件: {file_path}")

    df = pd.read_csv(file_path)

    # 默认返回 name 列作为列表
    if "name" in df.columns:
        return df["name"].dropna().unique().tolist()
    else:
        # 如果没有 name 列，就返回所有列名
        return df.columns.tolist()


#db_conn = connect_mongodb()
db_conn = None #+251205 Y.Huang
pokemons_list = get_db_item_list('airbyte_raw_Pokemon')
main_skills_list = get_db_item_list('airbyte_raw_MainSkill')
sub_skills_list = get_db_item_list('airbyte_raw_SubSkill')
natures_list = get_db_item_list('airbyte_raw_Nature')
ingredient_list = get_db_item_list('airbyte_raw_Ingredient')

# Free OCR API 配置（与 1_宝可梦潜力计算器.py 同步）
OCR_PAYLOAD = {
    "isOverlayRequired": False,
    "apikey": "K87144738488957",
    "language": "cht",
    "isTable": True,
}
OCR_ENDPOINT = "https://api.ocr.space/parse/image"

# ==================== 辅助函数 ====================

def correct_ocr_text(text):
    """
    应用OCR文字修正规则，处理常见的OCR误识别
    """
    if not isinstance(text, str):
        return text
    
    # 修正常见OCR错误
    corrections = {
        '技能提升M': '技能機率提升M',
        '技能提升1': '技能機率提升S',
        '技能提升m': '技能機率提升M',
        '技能提升s': '技能機率提升S',
        '食材提升M': '食材機率提升M',
        '食材提升S': '食材機率提升S',
        '幫手速度M': '幫忙速度M',
        '幫手速度S': '幫忙速度S',
        '持有上限提升M': '持有上限提升M',
        '持有上限提升S': '持有上限提升S',
        '樂天': '樂天',  # 性格名称
        '0隆隆石': '隆隆石',
        '0皮卡丘': '皮卡丘',
        'p537': '',  # 图鉴编号，去掉
    }
    
    for old, new in corrections.items():
        text = text.replace(old, new)
    
    # 去掉前导的纯数字或字母
    text = re.sub(r'^[\dA-Za-z]+', '', text)
    
    return text.strip()

def remove_english(text):
    """
    移除文本中的英文字母和数字，保留中文
    """
    if not isinstance(text, str):
        return text
    return re.sub(r'[A-Za-z0-9]', '', text).strip()

def extract_pokemon_name(text):
    """
    从文本中提取宝可梦名称，移除前缀如"Lv.30"或"p537"等
    """
    if not isinstance(text, str):
        return text
    
    # 移除前缀：数字、字母等
    extracted = re.sub(r'^[\dA-Za-z\.]+', '', text).strip()
    
    # 如果提取为空，返回原始文本
    if not extracted:
        return text
    
    return extracted

class TransformImage:
    def __init__(self, img):
        self.img = img
    
    def extract_text_from_img(self):
        """从图片中提取文字，使用 Free OCR API，返回文字列表"""
        try:
            # 调用 Free OCR API - 使用正确的文件格式
            # self.img 是 bytes，需要包装成文件对象
            files = {"file": ("image.jpg", self.img, "image/jpeg")}
            resp = requests.post(
                OCR_ENDPOINT,
                files=files,
                data=OCR_PAYLOAD,
                timeout=30
            )
            resp.raise_for_status()
            result_json = resp.json()
            
            # 调试：显示 API 原始返回
            with st.expander("🔍 Free OCR API 原始返回"):
                st.json(result_json)
            
            # 检查是否有错误
            if result_json.get("IsErroredOnProcessing"):
                st.error(f"❌ OCR API 处理错误: {result_json.get('ErrorMessage', '未知错误')}")
                return []
            
            # 提取文本
            all_texts = []
            for entry in result_json.get("ParsedResults", []):
                text_block = entry.get("ParsedText", "")
                if text_block:
                    # 按行拆分并过滤空行、时间戳、无关符号
                    lines = [ln.strip() for ln in text_block.split('\n') if ln.strip()]
                    # 过滤掉纯时间戳和无关项
                    filtered = []
                    for line in lines:
                        # 跳过时间戳、"返回"等无关项
                        if line in ['返回', '主技能/副技能', 'TextOrientation', '沒有性格帶來的特色']:
                            continue
                        # 跳过纯数字时间戳（如 18:25）
                        if ':' in line and all(c.isdigit() or c == ':' for c in line):
                            continue
                        # 跳过以 "Lv." 开头的等级标记（但保留含有技能的行）
                        if line.startswith('Lv.') and len(line) <= 5:
                            continue
                        filtered.append(line)
                    all_texts.extend(filtered)
            
            st.write("🔍 OCR 识别到的文本行数:", len(all_texts))
            if all_texts:
                with st.expander("📝 查看识别的原始文本"):
                    st.write(all_texts)
            else:
                st.warning("⚠️ OCR 未识别到任何文本")
            
            return all_texts
        except Exception as e:
            st.error(f"⚠️ OCR 识别异常: {str(e)}")
            import traceback
            with st.expander("🐛 错误详情"):
                st.code(traceback.format_exc())
            return []
            
    
    def filter_text(self, result):
        """
        从文字列表中提取宝可梦、技能等信息
        result: 文字列表 ['樹果', '×2', ..., '皮卡丘', ..., '樂天', ...]
        """
        if not result:
            st.warning("⚠️ filter_text 收到空列表")
            return {}
        
        # result 应该是一个简单的文字列表
        all_texts = result if isinstance(result, list) else [result]
        
        info = {}
        sub_skills_found = []  # 存储找到的副技能：(位置, 等级, 技能名)
        raw_texts_for_debug = []
        
        # 第一遍：收集所有信息
        for i, text in enumerate(all_texts):
            if not text or not isinstance(text, str):
                continue
            
            raw_texts_for_debug.append(text)
            
            # 应用所有OCR修正规则
            text_corrected = correct_ocr_text(text)
            
            # 检查是否匹配宝可梦（多个策略）
            if 'pokemon' not in info:
                # 策略1：精确匹配（修正后的文本）
                if text_corrected in pokemons_list:
                    info['pokemon'] = text_corrected
                # 策略2：包含匹配（文本中包含宝可梦名称的部分）
                else:
                    matched = False
                    for pokemon_name in pokemons_list:
                        # 长度 >= 2，避免单字符误匹配
                        if len(pokemon_name) >= 2:
                            # 精确包含
                            if pokemon_name in text_corrected:
                                info['pokemon'] = pokemon_name
                                matched = True
                                break
                            # 部分匹配（至少3个字符重合）
                            if len(pokemon_name) >= 3:
                                overlap = sum(1 for c in pokemon_name if c in text_corrected)
                                if overlap >= 2:
                                    info['pokemon'] = pokemon_name
                                    matched = True
                                    break
                    
                    # 策略3：尝试模糊匹配（如果前两个策略都失败）
                    if not matched and text_corrected:
                        for pokemon_name in pokemons_list:
                            # 计算相似度（简单的编辑距离或包含判断）
                            if len(text_corrected) >= 2 and len(pokemon_name) >= 2:
                                # 至少有2个字符在同一位置或相邻
                                common_chars = set(text_corrected) & set(pokemon_name)
                                if len(common_chars) >= 2:
                                    info['pokemon'] = pokemon_name
                                    break
            
            # 检查是否匹配主技能
            if text_corrected in main_skills_list and 'main_skill' not in info:
                info['main_skill'] = text_corrected
            # 检查是否匹配性格
            elif text_corrected in natures_list and 'nature' not in info:
                info['nature'] = text_corrected
            # 检查是否匹配副技能
            elif text_corrected in sub_skills_list:
                # 尝试从前面提取等级，如果没有则用位置作为排序依据
                level = self._extract_level_from_context(all_texts, i)
                sub_skills_found.append((i, level, text_corrected))
            # 尝试添加"持有"前缀
            elif f'持有{text_corrected}' in sub_skills_list:
                level = self._extract_level_from_context(all_texts, i)
                sub_skills_found.append((i, level, f'持有{text_corrected}'))
            # 模糊匹配副技能：尝试添加 S/M 后缀
            else:
                matched_skill = None
                for suffix in ['S', 'M']:
                    if f'{text_corrected}{suffix}' in sub_skills_list:
                        matched_skill = f'{text_corrected}{suffix}'
                        break
                    elif f'持有{text_corrected}{suffix}' in sub_skills_list:
                        matched_skill = f'持有{text_corrected}{suffix}'
                        break
                if matched_skill:
                    level = self._extract_level_from_context(all_texts, i)
                    sub_skills_found.append((i, level, matched_skill))
        
        # 第二遍：排序副技能
        # 启发式策略：按等级分组，同等级内的技能保持原始顺序
        # 这样可以在一定程度上恢复左右顺序，同时保留上下顺序
        
        # 按等级分组
        from collections import defaultdict
        level_groups = defaultdict(list)
        for pos, level, skill in sub_skills_found:
            level_groups[level].append((pos, level, skill))
        
        # 对每组内的技能按位置排序（保持原始顺序）
        for level in level_groups:
            level_groups[level].sort(key=lambda x: x[0])
        
        # 按等级排序，然后展平
        sorted_levels = sorted(level_groups.keys())
        sub_skills_found = []
        for level in sorted_levels:
            sub_skills_found.extend(level_groups[level])
        
        for idx, (pos, level, skill) in enumerate(sub_skills_found, start=1):
            if idx <= 5:  # 最多5个副技能
                info[f'sub_skill_{idx}'] = skill

        # 显示原始识别文本和提取结果
        with st.expander("📊 OCR原始文本分析"):
            st.write("**识别到的所有文本行（完整顺序）：**")
            for i, text in enumerate(raw_texts_for_debug):
                st.write(f"{i}: {text}")
            
            if sub_skills_found:
                st.write("**副技能识别顺序（排序前）：**")
                temp_before = [(pos, level, skill) for pos, level, skill in sub_skills_found]
                for pos, level, skill in temp_before:
                    level_str = f"Lv.{level}" if level != 999 else "无等级"
                    st.write(f"- 位置{pos}: {level_str} - {skill}")
        
        if info:
            with st.expander("✅ 提取到的信息（排序后）"):
                st.json(info)
                if sub_skills_found:
                    st.write("**最终副技能顺序：**")
                    for pos, level, skill in sub_skills_found:
                        level_str = f"Lv.{level}" if level != 999 else "无等级"
                        st.write(f"- {level_str}: {skill}")
        else:
            st.warning("⚠️ 未能从文本中提取到有效信息，请检查：")
            st.write("1. 🖼️ 宝可梦截图是否清晰")
            st.write("2. 📋 上方 OCR 原始文本中是否包含宝可梦名字")
            st.write("3. 📚 宝可梦名字是否在数据库中")
        
        return info
    
    def _extract_level_from_context(self, all_texts, current_index):
        """
        从当前文本的上下文中提取等级信息（如 Lv.25）
        返回等级数字，默认返回 999（表示未找到等级）
        
        搜索策略：
        1. 先检查当前行本身
        2. 再检查前5行（向前搜索）
        3. 最后检查后2行（向后搜索）
        """
        # 检查模式：Lv. 或 Lv 后跟数字
        level_pattern = re.compile(r'Lv\.?(\d+)', re.IGNORECASE)
        
        # 策略1：检查当前行本身
        match = level_pattern.search(all_texts[current_index])
        if match:
            return int(match.group(1))
        
        # 策略2：检查前面的行（最多5行）
        for offset in range(-1, -6, -1):  # -1, -2, -3, -4, -5
            check_idx = current_index + offset
            if 0 <= check_idx < len(all_texts):
                match = level_pattern.search(all_texts[check_idx])
                if match:
                    return int(match.group(1))
        
        # 策略3：检查后面的行（最多2行）
        for offset in range(1, 3):  # +1, +2
            check_idx = current_index + offset
            if 0 <= check_idx < len(all_texts):
                match = level_pattern.search(all_texts[check_idx])
                if match:
                    return int(match.group(1))
        
        # 未找到等级
        return 999
    
    def run(_self):
        result = _self.extract_text_from_img()
        info = _self.filter_text(result)
        
        # 调试：如果识别不到宝可梦，显示数据库前20个宝可梦供参考
        if 'pokemon' not in info and pokemons_list:
            with st.expander("📖 数据库中的宝可梦示例（前30个）"):
                st.write(pokemons_list[:30])
        
        print(f"{datetime.now()}")
        print(f"{info}")
        print("=========")
        return info
