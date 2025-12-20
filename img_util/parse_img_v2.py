import re
from datetime import datetime
import streamlit as st
import warnings; warnings.filterwarnings('ignore')
import requests
import os
import pandas as pd
import cv2
import numpy as np
from io import BytesIO

raw_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "dbdata")

def get_db_item_list(collection_name: str):
    """从 /data/dbdata 下的 CSV 文件读取数据"""
    file_path = os.path.join(raw_DATA_DIR, f"{collection_name}.csv")
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"找不到文件: {file_path}")
    df = pd.read_csv(file_path)
    if "name" in df.columns:
        return df["name"].dropna().unique().tolist()
    else:
        return df.columns.tolist()

pokemons_list = get_db_item_list('airbyte_raw_Pokemon')
main_skills_list = get_db_item_list('airbyte_raw_MainSkill')
sub_skills_list = get_db_item_list('airbyte_raw_SubSkill')
natures_list = get_db_item_list('airbyte_raw_Nature')
ingredient_list = get_db_item_list('airbyte_raw_Ingredient')

# Free OCR API 配置
OCR_PAYLOAD = {
    "isOverlayRequired": False,
    "apikey": "K87144738488957",
    "language": "cht",
    "isTable": True,  # 启用表格识别
}
OCR_ENDPOINT = "https://api.ocr.space/parse/image"

# ==================== 辅助函数 ====================

def correct_ocr_text(text):
    """应用OCR文字修正规则"""
    if not isinstance(text, str):
        return text
    
    corrections = {
        'p537': '',
        'P310': '',
        'p756': '',
        'LV.IO': 'Lv.10',
        '每42分33秒': '',
        '每1小時': '',
        # 文字异体字统一（OCR易识别为日文/简体异体）
        '呑': '吞',
        '兽': '獸',
    }
    
    for old, new in corrections.items():
        text = text.replace(old, new)
    
    # 去掉前导噪声（保留以 Lv. 开头的等级标记）
    if not re.match(r'^\s*Lv\.?\d+', text, flags=re.IGNORECASE):
        # 先去掉以 p/P+数字 形式的噪声前缀
        text = re.sub(r'^[Pp]\d+', '', text)
        # 再去掉前导的 @ 或 纯数字
        text = re.sub(r'^[@\d]+', '', text)

    # 统一全角数字/字母为半角，并移除前导的零（例如 "0皮卡丘" → "皮卡丘"）
    text = text.translate(str.maketrans('０１２３４５６７８９ｓｍＳＭ', '0123456789smSM'))
    text = re.sub(r'^0+', '', text)
    
    # 重要：将末尾或空白前的 s/m 等级后缀统一为大写（适配中文+字母结尾）
    text = re.sub(r's(?=$|\s|\t)', 'S', text, flags=re.IGNORECASE)
    text = re.sub(r'm(?=$|\s|\t)', 'M', text, flags=re.IGNORECASE)
    
    return text.strip()

class TransformImage:
    def __init__(self, img):
        self.img = img
    
    def extract_text_from_img(self):
        """从图片中提取文字，使用 Free OCR API"""
        try:
            files = {"file": ("image.jpg", self.img, "image/jpeg")}
            resp = requests.post(
                OCR_ENDPOINT,
                files=files,
                data=OCR_PAYLOAD,
                timeout=30
            )
            resp.raise_for_status()
            result_json = resp.json()
            
            with st.expander("🔍 Free OCR API 原始返回"):
                st.json(result_json)
            
            if result_json.get("IsErroredOnProcessing"):
                st.error(f"❌ OCR API 处理错误: {result_json.get('ErrorMessage', '未知错误')}")
                return []
            
            # 提取文本
            all_texts = []
            for entry in result_json.get("ParsedResults", []):
                text_block = entry.get("ParsedText", "")
                if text_block:
                    lines = [ln.strip() for ln in text_block.split('\n') if ln.strip()]
                    filtered = []
                    for line in lines:
                        if line in ['返回', '主技能/副技能', 'TextOrientation', '沒有性格帶來的特色']:
                            continue
                        if ':' in line and all(c.isdigit() or c == ':' for c in line):
                            continue
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
        """从文字列表中提取宝可梦、技能等信息"""
        if not result:
            st.warning("⚠️ filter_text 收到空列表")
            return {}
        
        all_texts = result if isinstance(result, list) else [result]
        info = {}
        sub_skills_found = []  # (原始位置, 技能名) - 保持OCR识别顺序
        
        # 调试：显示原始与修正后的文本，便于确认清洗效果
        with st.expander("📋 识别文本（原始 → 修正）"):
            for i, text in enumerate(all_texts):
                corrected = correct_ocr_text(text)
                st.write(f"{i}: `{text}` → `{corrected}`")
        
        # 第一遍：收集所有信息
        for i, text in enumerate(all_texts):
            if not text or not isinstance(text, str):
                continue
            
            text_corrected = correct_ocr_text(text)
            
            # 检查是否包含制表符（表格模式会把同行的多个技能用制表符分隔）
            texts_to_check = [text_corrected]
            if '\t' in text_corrected:
                texts_to_check = [t.strip() for t in text_corrected.split('\t') if t.strip()]
            
            for text_part in texts_to_check:
                # 宝可梦匹配（优先精确匹配，再尝试包含匹配）
                if 'pokemon' not in info:
                    if text_part in pokemons_list:
                        info['pokemon'] = text_part
                    else:
                        # 尝试模糊匹配：宝可梦名称在文本中
                        for pokemon_name in pokemons_list:
                            if len(pokemon_name) >= 2 and pokemon_name in text_part:
                                info['pokemon'] = pokemon_name
                                break
                        # 如果还没找到，反过来尝试：文本在某个宝可梦名称中
                        if 'pokemon' not in info:
                            for pokemon_name in pokemons_list:
                                if len(text_part) >= 2 and text_part in pokemon_name:
                                    info['pokemon'] = pokemon_name
                                    break
                
                # 主技能匹配
                if text_part in main_skills_list and 'main_skill' not in info:
                    info['main_skill'] = text_part
                
                # 性格匹配
                elif text_part in natures_list and 'nature' not in info:
                    info['nature'] = text_part
                
                # 副技能匹配（只在位置7之后，保持OCR识别顺序）
                elif i >= 7:
                    matched_skill = self._match_sub_skill(text_part)
                    if matched_skill:
                        sub_skills_found.append((i, matched_skill))
                        st.write(f"✓ 匹配副技能：`{text_part}` → `{matched_skill}`")
        
        # 按OCR识别顺序填充副技能（不重新排序）
        for idx, (pos, skill) in enumerate(sub_skills_found, start=1):
            if idx <= 5:
                info[f'sub_skill_{idx}'] = skill
        
        # 调试输出
        with st.expander("✅ 提取到的信息"):
            st.json(info)
            if sub_skills_found:
                st.write(f"**识别到 {len(sub_skills_found)} 个副技能（按OCR识别顺序）：**")
                for idx, (pos, skill) in enumerate(sub_skills_found, start=1):
                    st.write(f"{idx}. 位置{pos}: {skill}")
            else:
                st.warning("⚠️ 未识别到任何副技能")
        
        return info
    
    def _match_sub_skill(self, text):
        """尝试匹配副技能（优先精确匹配）"""
        # 第一级：精确匹配
        if text in sub_skills_list:
            return text
        
        # 第二级：加前缀精确匹配
        if f'持有{text}' in sub_skills_list:
            return f'持有{text}'
        
        # 第三级：加后缀精确匹配（S/M 等级）
        for suffix in ['S', 'M', 's', 'm']:
            if f'{text}{suffix}' in sub_skills_list:
                return f'{text}{suffix}'
            if f'持有{text}{suffix}' in sub_skills_list:
                return f'持有{text}{suffix}'
        
        # 第四级：模糊匹配
        for skill in sub_skills_list:
            # 检查技能名在文本中
            if len(skill) >= 3 and skill in text:
                return skill
            # 检查文本在技能名中
            if len(text) >= 3 and text in skill:
                return skill
        
        return None
    
    def _extract_level_from_context(self, all_texts, current_index):
        """从上下文中提取等级"""
        level_pattern = re.compile(r'Lv\.?(\d+)', re.IGNORECASE)
        
        # 检查当前行
        if level_pattern.search(all_texts[current_index]):
            return int(level_pattern.search(all_texts[current_index]).group(1))
        
        # 检查前5行
        for offset in range(-1, -6, -1):
            if 0 <= current_index + offset < len(all_texts):
                match = level_pattern.search(all_texts[current_index + offset])
                if match:
                    return int(match.group(1))
        
        # 检查后2行
        for offset in range(1, 3):
            if 0 <= current_index + offset < len(all_texts):
                match = level_pattern.search(all_texts[current_index + offset])
                if match:
                    return int(match.group(1))
        
        return 999
    
    def _extract_position_from_table(self, all_texts, current_index):
        """从表格结构推断行列位置"""
        level_pattern = re.compile(r'Lv\.?(\d+)', re.IGNORECASE)
        
        # 检查当前行是否有制表符（表格模式的标志）
        current_text = all_texts[current_index]
        has_tab = '\t' in current_text
        
        # 收集所有等级标记的位置
        level_positions = []
        for i, text in enumerate(all_texts):
            if level_pattern.search(text):
                level_positions.append(i)
        
        if not level_positions:
            return (999, 999)
        
        # 找最接近的等级标记（在当前行之前）
        row = 0
        col = 0
        closest_level_idx = None
        
        for idx, pos in enumerate(level_positions):
            if pos < current_index:
                closest_level_idx = idx
            else:
                break
        
        if closest_level_idx is None:
            return (0, 0)
        
        # 计算行号
        closest_level_pos = level_positions[closest_level_idx]
        row_count = 0
        for i in range(closest_level_idx):
            # 如果相邻两个等级标记距离 > 2，说明换行了
            if i > 0 and level_positions[i] - level_positions[i-1] > 2:
                row_count += 1
        if closest_level_idx > 0:
            row_count += level_positions[closest_level_idx] - level_positions[closest_level_idx - 1] > 2
        
        # 简化：直接数有多少个等级标记在当前位置之前，且它们相距较远（>2）
        row = 0
        for i in range(closest_level_idx):
            if i == 0 or level_positions[i] - level_positions[i-1] > 2:
                row += 1
        
        # 列号判断：如果当前行的下一个等级标记在接近的位置（< 3 行），则为右列
        col = 0
        if closest_level_idx + 1 < len(level_positions):
            next_level_pos = level_positions[closest_level_idx + 1]
            # 如果下一个等级标记在近距离（2-3行内），说明在同一行，这是右列
            if 0 < next_level_pos - closest_level_pos <= 3:
                col = 1
        
        return (row, col)
    
    def run(_self):
        result = _self.extract_text_from_img()
        info = _self.filter_text(result)
        print(f"{datetime.now()}: {info}")
        return info
