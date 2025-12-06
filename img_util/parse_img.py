import re
import streamlit as st
#from pymongo.mongo_client import MongoClient
import warnings; warnings.filterwarnings('ignore')
from paddleocr import PaddleOCR
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
def load_ocr(lang="chinese_cht"):
    return PaddleOCR(lang=lang)

class TransformImage:
    def __init__(self, img):
        self.img = img
        self.lang = "chinese_cht"
        self.ocr = load_ocr()   # 缓存的 OCR 实例

    def extract_text_from_img(self):
        try:
            nparr = np.frombuffer(self.img, np.uint8)
            img_array = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img_array is None:
                return []
        except Exception:
            return []

        try:
            result = self.ocr.ocr(img_array)
            all_texts = []
            if result and len(result) > 0:
                ocr_result = result[0]
                if hasattr(ocr_result, 'rec_texts'):
                    all_texts = list(ocr_result.rec_texts)
                elif isinstance(ocr_result, dict) and 'rec_texts' in ocr_result:
                    all_texts = ocr_result['rec_texts']
                elif isinstance(ocr_result, list):
                    all_texts = [line[1][0] for line in ocr_result if isinstance(line, (list, tuple)) and len(line) > 1]
            return all_texts
        except Exception:
            return []         
    
    def filter_text(self, result):
        """
        从文字列表中提取宝可梦、技能等信息
        result: 文字列表 ['樹果', '×2', ..., '皮卡丘', ..., '樂天', ...]
        """
        
        def sub_eng(text):
            # 移除英文字
            return re.sub(u'[A-Za-z]', '', text)
        
        if not result:
            return {}
        
        # result 应该是一个简单的文字列表
        all_texts = result if isinstance(result, list) else [result]
        
        info = {}
        sub_skill_idx = 1
        
        for idx, text in enumerate(all_texts):
            if not text or not isinstance(text, str):
                continue
                
            text = text.strip()
            
            # 对于中文文本，不要做大写转换，直接匹配
            # 但英文部分需要转大写用于匹配
            text_upper = text.upper()
            text_no_eng = sub_eng(text_upper)  # 去掉英文后可能还有中文
            
            # 检查是否匹配宝可梦（直接用原始文本和去英文版本）
            if text in pokemons_list:
                info['pokemon'] = text
            elif text_no_eng in pokemons_list:
                info['pokemon'] = text_no_eng
            # 检查是否匹配主技能
            elif text in main_skills_list:
                info['main_skill'] = text
            elif text.replace('瘋', '癒') in main_skills_list:
                info['main_skill'] = text.replace('瘋', '癒')
            elif text.replace('癥', '癒') in main_skills_list:
                info['main_skill'] = text.replace('癥', '癒')
            # 检查是否匹配性格
            elif text in natures_list:
                info['nature'] = text
            elif text.replace('青', '害') in natures_list:
                info['nature'] = text.replace('青', '害')
            # 检查是否匹配副技能
            elif text in sub_skills_list:
                info[f'sub_skill_{sub_skill_idx}'] = text
                sub_skill_idx += 1
            elif text.replace('盜', '持') in sub_skills_list:
                info[f'sub_skill_{sub_skill_idx}'] = text.replace('盜', '持')
                sub_skill_idx += 1
            elif text.replace('複', '復') in sub_skills_list:
                info[f'sub_skill_{sub_skill_idx}'] = text.replace('複', '復')
                sub_skill_idx += 1
            elif f'持有{text}' in sub_skills_list:
                info[f'sub_skill_{sub_skill_idx}'] = f'持有{text}'
                sub_skill_idx += 1 
            else:
                text_replaced = text.replace('盜', '持')
                if f'持有{text_replaced}' in sub_skills_list:
                    info[f'sub_skill_{sub_skill_idx}'] = f'持有{text_replaced}'
                    sub_skill_idx += 1 

        return info
    
    def run(_self):
        result = _self.extract_text_from_img()
        info = _self.filter_text(result)
        return info
