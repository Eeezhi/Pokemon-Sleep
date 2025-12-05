import re
from datetime import datetime
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

class TransformImage:
    def __init__(self, img):
        self.img = img
        self.lang = "chinese_cht"
    
    def extract_text_from_img(self):
        """从图片中提取文字，返回文字列表"""
        print(f"[DEBUG] 输入图片类型: {type(self.img)}, 大小: {len(self.img) if isinstance(self.img, bytes) else 'N/A'}")
        
        # 将字节流转换为 numpy 数组
        try:
            nparr = np.frombuffer(self.img, np.uint8)
            img_array = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            print(f"[DEBUG] 图片转换成功，shape: {img_array.shape if img_array is not None else 'None'}")
            
            if img_array is None:
                print(f"[ERROR] 图片解码失败，img_array 为 None")
                return []
        except Exception as e:
            print(f"[ERROR] 图片转换失败: {e}")
            return []
        
        try:
            ocr = PaddleOCR(lang=self.lang)  
            print(f"[DEBUG] PaddleOCR 初始化成功")
        except Exception as e:
            print(f"[ERROR] PaddleOCR 初始化失败: {e}")
            return []
        
        try:
            # 使用 ocr() 方法
            result = ocr.ocr(img_array)  
            print(f"[DEBUG] OCR ocr() 返回类型: {type(result)}")
            
            # PaddleOCR 返回的是 [PPStructure 对象] 或直接的文字列表
            # 需要从中提取 rec_texts
            all_texts = []
            
            if result and len(result) > 0:
                ocr_result = result[0]
                print(f"[DEBUG] result[0] 类型: {type(ocr_result)}")
                
                # 如果有 rec_texts 属性（PPStructure 返回），提取它
                if hasattr(ocr_result, 'rec_texts'):
                    all_texts = list(ocr_result.rec_texts)
                    print(f"[DEBUG] 从 rec_texts 提取文字: {all_texts}")
                # 如果是字典，也许有 rec_texts
                elif isinstance(ocr_result, dict) and 'rec_texts' in ocr_result:
                    all_texts = ocr_result['rec_texts']
                    print(f"[DEBUG] 从字典 rec_texts 提取文字: {all_texts}")
                # 如果是 PaddleOCR 原始格式（嵌套列表）
                elif isinstance(ocr_result, list):
                    all_texts = [line[1][0] for line in ocr_result if isinstance(line, (list, tuple)) and len(line) > 1]
                    print(f"[DEBUG] 从嵌套列表提取文字: {all_texts}")
                
                print(f"[DEBUG] 最终提取的文字数: {len(all_texts)}, 内容: {all_texts}")
                return all_texts
            else:
                print(f"[DEBUG] OCR 结果为空")
                return []
                
        except Exception as e:
            print(f"[ERROR] OCR 处理失败: {e}")
            import traceback
            traceback.print_exc()
            return []
            
    
    def filter_text(self, result):
        """
        从文字列表中提取宝可梦、技能等信息
        result: 文字列表 ['樹果', '×2', ..., '皮卡丘', ..., '樂天', ...]
        """
        
        def sub_eng(text):
            # 移除英文字
            return re.sub(u'[A-Za-z]', '', text)
        
        # 调试：打印输入
        print(f"[DEBUG] filter_text 输入 result 类型: {type(result)}, 长度: {len(result) if isinstance(result, (list, tuple)) else 'N/A'}")
        print(f"[DEBUG] result 前 10 项: {result[:10] if isinstance(result, (list, tuple)) else result}")
        
        if not result:
            print(f"[DEBUG] result 为空，直接返回空 info")
            return {}
        
        # result 应该是一个简单的文字列表
        all_texts = result if isinstance(result, list) else [result]
        
        print(f"[DEBUG] 处理的文字列表: {all_texts}")
        print(f"[DEBUG] 宝可梦列表样本 (前10个): {pokemons_list[:10]}")
        print(f"[DEBUG] 宝可梦列表总数: {len(pokemons_list)}")
        print(f"[DEBUG] 性格列表样本 (前10个): {natures_list[:10] if natures_list else 'Empty'}")
        print(f"[DEBUG] 性格列表总数: {len(natures_list) if natures_list else 0}")
        print(f"[DEBUG] 主技能列表样本 (前10个): {main_skills_list[:10] if main_skills_list else 'Empty'}")
        print(f"[DEBUG] 副技能列表样本 (前10个): {sub_skills_list[:10] if sub_skills_list else 'Empty'}")
        
        # 特别调试：直接查找关键词
        print(f"[DEBUG] '皮卡丘' 在 pokemons_list 中? {('皮卡丘' in pokemons_list)}")
        print(f"[DEBUG] '樂天' 在 natures_list 中? {('樂天' in natures_list)}")
        
        # 打印列表中包含"皮"和"樂"的项
        pikachu_candidates = [p for p in pokemons_list if '皮' in p]
        nature_candidates = [n for n in natures_list if '樂' in n or '天' in n]
        print(f"[DEBUG] pokemons_list 中包含'皮'的项: {pikachu_candidates}")
        print(f"[DEBUG] natures_list 中包含'樂'或'天'的项: {nature_candidates}")
        
        info = {}
        sub_skill_idx = 1
        
        for idx, text in enumerate(all_texts):
            if not text or not isinstance(text, str):
                continue
                
            text = text.strip()
            print(f"[DEBUG] 处理第 {idx} 项文字: '{text}'")
            
            # 对于中文文本，不要做大写转换，直接匹配
            # 但英文部分需要转大写用于匹配
            text_upper = text.upper()
            text_no_eng = sub_eng(text_upper)  # 去掉英文后可能还有中文
            
            # 检查是否匹配宝可梦（直接用原始文本和去英文版本）
            if text in pokemons_list:
                info['pokemon'] = text
                print(f"[DEBUG] ✓ 匹配到宝可梦 (直接): {info['pokemon']}")
            elif text_no_eng in pokemons_list:
                info['pokemon'] = text_no_eng
                print(f"[DEBUG] ✓ 匹配到宝可梦 (去英文): {info['pokemon']}")
            # 检查是否匹配主技能
            elif text in main_skills_list:
                info['main_skill'] = text
                print(f"[DEBUG] ✓ 匹配到主技能: {info['main_skill']}")
            elif text.replace('瘋', '癒') in main_skills_list:
                info['main_skill'] = text.replace('瘋', '癒')
                print(f"[DEBUG] ✓ 匹配到主技能 (替换瘋癒): {info['main_skill']}")
            elif text.replace('癥', '癒') in main_skills_list:
                info['main_skill'] = text.replace('癥', '癒')
                print(f"[DEBUG] ✓ 匹配到主技能 (替换癥癒): {info['main_skill']}")
            # 检查是否匹配性格
            elif text in natures_list:
                info['nature'] = text
                print(f"[DEBUG] ✓ 匹配到性格 (直接): {info['nature']}")
            elif text.replace('青', '害') in natures_list:
                info['nature'] = text.replace('青', '害')
                print(f"[DEBUG] ✓ 匹配到性格 (替换青害): {info['nature']}")
            # 检查是否匹配副技能
            elif text in sub_skills_list:
                info[f'sub_skill_{sub_skill_idx}'] = text
                print(f"[DEBUG] ✓ 匹配到副技能 {sub_skill_idx}: {info[f'sub_skill_{sub_skill_idx}']}")
                sub_skill_idx += 1
            elif text.replace('盜', '持') in sub_skills_list:
                info[f'sub_skill_{sub_skill_idx}'] = text.replace('盜', '持')
                print(f"[DEBUG] ✓ 匹配到副技能 {sub_skill_idx} (替换盜持): {info[f'sub_skill_{sub_skill_idx}']}")
                sub_skill_idx += 1
            elif text.replace('複', '復') in sub_skills_list:
                info[f'sub_skill_{sub_skill_idx}'] = text.replace('複', '復')
                print(f"[DEBUG] ✓ 匹配到副技能 {sub_skill_idx} (替换複復): {info[f'sub_skill_{sub_skill_idx}']}")
                sub_skill_idx += 1
            elif f'持有{text}' in sub_skills_list:
                info[f'sub_skill_{sub_skill_idx}'] = f'持有{text}'
                skill_name = info[f'sub_skill_{sub_skill_idx}']
                print(f"[DEBUG] ✓ 匹配到持有技能 {sub_skill_idx}: {skill_name}")
                sub_skill_idx += 1 
            else:
                text_replaced = text.replace('盜', '持')
                if f'持有{text_replaced}' in sub_skills_list:
                    info[f'sub_skill_{sub_skill_idx}'] = f'持有{text_replaced}'
                    skill_name = info[f'sub_skill_{sub_skill_idx}']
                    print(f"[DEBUG] ✓ 匹配到持有技能 {sub_skill_idx} (替换): {skill_name}")
                    sub_skill_idx += 1 
                else:
                    print(f"[DEBUG] ✗ 未匹配任何项目")

        print(f"[DEBUG] 最终提取的 info: {info}")
        return info
    
    def run(_self):
        result = _self.extract_text_from_img()
        info = _self.filter_text(result)
        print(f"{datetime.now()}")
        print(f"{info}")
        print("=========")
        return info
