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
from img_util.text_correction import correct_ocr_text, remove_english, extract_pokemon_name

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

    def preprocess_image(self, img_array):
        """图像预处理，提高OCR识别率"""
        # 1. 转灰度
        gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)
        
        # 2. 降噪
        denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
        
        # 3. 自适应二值化（对不同亮度区域效果更好）
        binary = cv2.adaptiveThreshold(
            denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        
        # 4. 锐化（可选，增强边缘）
        kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
        sharpened = cv2.filter2D(binary, -1, kernel)
        
        # 5. 调整对比度
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(denoised)
        
        return enhanced
    
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
            # 图像预处理
            processed_img = self.preprocess_image(img_array)
            
            # 用 EasyOCR 识别繁体中文（使用预处理后的图像）
            result = self.ocr.readtext(processed_img, detail=1)
            # EasyOCR 返回 [(bbox, text, confidence), ...]
            # 提取所有文本，不过滤置信度
            all_texts = [text.strip() for (bbox, text, conf) in result if text.strip()]
            
            # 临时调试：显示识别到的原始文本和置信度
            st.write("🔍 OCR 识别到的文本行数:", len(all_texts))
            if all_texts:
                with st.expander("📝 查看识别的原始文本（带置信度）"):
                    for (bbox, text, conf) in result:
                        if text.strip():
                            st.write(f"{text.strip()} (置信度: {conf:.2f})")
            else:
                st.warning("⚠️ OCR 未识别到任何文本")
            
            return all_texts
        except Exception as e:
            st.error(f"⚠️ OCR 识别异常: {str(e)}")
            return []
       
    
    def filter_text(self, result):
        
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
            
            # 应用所有OCR修正规则
            text = correct_ocr_text(text)
            
            # 对于中文文本，不要做大写转换，直接匹配
            # 但英文部分需要转大写用于匹配
            text_upper = text.upper()
            text_no_eng = remove_english(text_upper)  # 去掉英文后可能还有中文
            
            # 尝试从文本中提取宝可梦名字（移除Lv.前缀）
            pokemon_name_extracted = extract_pokemon_name(text)
            
            # 检查是否匹配宝可梦（直接用原始文本和去英文版本）
            if text in pokemons_list:
                info['pokemon'] = text
            elif text_no_eng in pokemons_list:
                info['pokemon'] = text_no_eng
            elif pokemon_name_extracted in pokemons_list:
                # 匹配去除Lv.前缀后的名字
                info['pokemon'] = pokemon_name_extracted
            # 模糊匹配宝可梦（检查文本中是否包含宝可梦名称）
            elif 'pokemon' not in info:
                for pokemon_name in pokemons_list:
                    if len(pokemon_name) >= 3 and (pokemon_name in text or pokemon_name in pokemon_name_extracted):
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
            
            # 如果没有识别到宝可梦，显示可能的宝可梦名字供手动选择
            if 'pokemon' not in info:
                st.warning("⚠️ 未能识别到宝可梦，可能原因：")
                st.write("1. 宝可梦不在数据库中")
                st.write("2. OCR识别文字有误")
                st.write("3. 请检查识别的原始文本中是否包含宝可梦名字")
        else:
            st.warning("⚠️ 未能从文本中提取到有效信息")
        
        return info
    
    def run(_self):
        result = _self.extract_text_from_img()
        info = _self.filter_text(result)
        return info
