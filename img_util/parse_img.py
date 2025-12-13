import re
import streamlit as st
#from pymongo.mongo_client import MongoClient
import warnings; warnings.filterwarnings('ignore')
import easyocr
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

@st.cache_resource
def load_ocr():
    """加载 EasyOCR Reader，使用繁体中文模型"""
    return easyocr.Reader(['ch_tra'], gpu=False)

class TransformImage:
    def __init__(self, img):
        self.img = img
        self.ocr = load_ocr()   # 缓存的 EasyOCR Reader 实例

    def extract_text_from_img(self):
        try:
            # 将二进制数据转成 OpenCV 图像
            nparr = np.frombuffer(self.img, np.uint8)
            img_array = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img_array is None:
                st.error("⚠️ 图像解码失败")
                return []
        except Exception as e:
            st.error(f"⚠️ 图像读取异常: {str(e)}")
            return []

        try:
            # 用 EasyOCR 识别繁体中文
            result = self.ocr.readtext(img_array)
            # EasyOCR 返回 [(bbox, text, confidence), ...]
            # 提取所有文本
            all_texts = [text.strip() for (bbox, text, conf) in result if text.strip()]
            
            # 临时调试：显示识别到的原始文本
            st.write("🔍 OCR 识别到的文本行数:", len(all_texts))
            if all_texts:
                with st.expander("📝 查看识别的原始文本"):
                    st.write(all_texts)
            else:
                st.warning("⚠️ OCR 未识别到任何文本")
            
            return all_texts
        except Exception as e:
            st.error(f"⚠️ OCR 识别异常: {str(e)}")
            return []
       
    
    def filter_text(self, result):
        
        def sub_eng(text):
            # 移除英文字
            return re.sub(u'[A-Za-z]', '', text)
        
        if not result:
            st.warning("⚠️ filter_text 收到空列表")
            return {}
        
        # result 应该是一个简单的文字列表
        all_texts = result if isinstance(result, list) else [result]
        
        info = {}
        sub_skill_idx = 1
        
        for idx, text in enumerate(all_texts):
            if not text or not isinstance(text, str):
                continue
                
            text = text.strip()
            
            # OCR 常见错误修正（EasyOCR 特定）
            text = text.replace('$', 'S')  # $ → S
            text = text.replace('|', 'S')  # | → S
            text = text.replace('兔', 'S')  # 兔 → S
            text = text.replace('瘋', '癒')  # 瘋 → 癒
            text = text.replace('癥', '癒')  # 癥 → 癒
            text = text.replace('青', '害')  # 青 → 害
            text = text.replace('盜', '持')  # 盜 → 持
            text = text.replace('複', '復')  # 複 → 復
            text = text.replace('凶', 'M')  # 凶 → M
            text = text.replace('日', 'M')  # 日 → M
            text = text.replace('氏', 'E')  # 氏 → E (睡眠EXP)
            text = text.replace('人?', 'XP')  # 人? → XP (EXP)
            
            # 修正技能等级后缀（S/M/L）
            # 数字 5 → S
            if '速度5' in text or '提升5' in text or '上限5' in text:
                text = text.replace('速度5', '速度S').replace('提升5', '提升S').replace('上限5', '上限S')
            
            # 修正睡眠EXP相关错误
            if '睡眠E' in text and 'XP' not in text:
                text = text.replace('睡眠E', '睡眠EXP')
            if 'EXP獲得量' in text:
                text = text.replace('EXP獲得量', 'EXP獎勵')
            
            # 技能名称中的 1 → M（只在特定上下文中替换）
            if '提升1' in text or '提升l' in text:
                text = text.replace('提升1', '提升M').replace('提升l', '提升M')
            if '上限1' in text or '上限l' in text:
                text = text.replace('上限1', '上限M').replace('上限l', '上限M')
            
            # 对于中文文本，不要做大写转换，直接匹配
            # 但英文部分需要转大写用于匹配
            text_upper = text.upper()
            text_no_eng = sub_eng(text_upper)  # 去掉英文后可能还有中文
            
            # 检查是否匹配宝可梦（直接用原始文本和去英文版本）
            if text in pokemons_list:
                info['pokemon'] = text
            elif text_no_eng in pokemons_list:
                info['pokemon'] = text_no_eng
            # 模糊匹配宝可梦（检查文本中是否包含宝可梦名称）
            elif 'pokemon' not in info:
                for pokemon_name in pokemons_list:
                    if len(pokemon_name) >= 3 and pokemon_name in text:
                        info['pokemon'] = pokemon_name
                        break
            
            # 检查是否匹配主技能
            if text in main_skills_list:
                info['main_skill'] = text
            # 检查是否匹配性格
            elif text in natures_list:
                info['nature'] = text
            # 检查是否匹配副技能
            elif text in sub_skills_list:
                info[f'sub_skill_{sub_skill_idx}'] = text
                sub_skill_idx += 1
            # 尝试添加"持有"前缀
            elif f'持有{text}' in sub_skills_list:
                info[f'sub_skill_{sub_skill_idx}'] = f'持有{text}'
                sub_skill_idx += 1
            # 模糊匹配副技能：尝试添加 S/M/L 后缀
            else:
                matched = False
                for suffix in ['S', 'M', 'L']:
                    if f'{text}{suffix}' in sub_skills_list:
                        info[f'sub_skill_{sub_skill_idx}'] = f'{text}{suffix}'
                        sub_skill_idx += 1
                        matched = True
                        break
                    elif f'持有{text}{suffix}' in sub_skills_list:
                        info[f'sub_skill_{sub_skill_idx}'] = f'持有{text}{suffix}'
                        sub_skill_idx += 1
                        matched = True
                        break 

        # 临时调试：显示提取到的信息
        if info:
            with st.expander("✅ 提取到的信息"):
                st.json(info)
        else:
            st.warning("⚠️ 未能从文本中提取到有效信息")
        
        return info
    
    def run(_self):
        result = _self.extract_text_from_img()
        info = _self.filter_text(result)
        return info
