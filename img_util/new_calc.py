import numpy as np
import pandas as pd
import os

#全新计算方法 Y.Huang 2025.12.20

# 获取当前脚本目录的上层（Pokemon-Sleep），以便访问 data/ 文件夹
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EFFICIENT_DIR = os.path.join(BASE_DIR, 'data', 'Efficient')

def has_helper_bonus(sub_skills):
    """检查副技能中是否包含幫手獎勵"""
    return '幫手獎勵' in sub_skills


def get_pokemon_type(pokemon_info):
    """从 pokemon_info 中提取类型，兼容 dict 和 pandas.Series。"""
    if pokemon_info is None:
        raise ValueError("pokemon_info 不能为空")
    if isinstance(pokemon_info, dict):
        return pokemon_info.get('type')
    if hasattr(pokemon_info, '__contains__') and 'type' in pokemon_info:
        return pokemon_info['type']
    raise KeyError("未在 pokemon_info 中找到 'type' 字段")

def has_fruit_bonus(sub_skills):
    """检查副技能中是否包含樹果獎勵"""
    return '樹果數量S' in sub_skills

def fruit_type(sub_skills, nature_up, nature_down):
    """對樹果型寶可夢進行計算"""
    help_bonus = has_helper_bonus(sub_skills)
    fruit_s = has_fruit_bonus(sub_skills)
    help_speed = get_help_speed(sub_skills)
    
    # 初始化默认值
    score = None
    result = None
        
    # 读取效率数据
    efficient_data = pd.read_csv(os.path.join(EFFICIENT_DIR, 'Efficient_help_fruit.csv'))
    # 根据fruit_s和help_speed筛选数据
    filtered_data = efficient_data[
            (efficient_data['help_bonus'] == int(help_bonus)) &
            (efficient_data['fruit_s'] == fruit_s) & 
            (efficient_data['help_speed'] == help_speed)
        ]
    if filtered_data.empty:
        result = "宝可梦不可用" 
    else:
        for j in filtered_data.itertuples():
            if nature_up == '幫忙速度':
                score = j.nature_help_up
                result = j.result1
            elif nature_down == '幫忙速度':
                score = j.nature_help_down
                result = j.result3
            else:
                score = j.nature_help_none
                result = j.result2
    return score, result
        
def skill_type(sub_skills, nature_up, nature_down):
    """對技能型寶可夢進行計算"""
    # 使用副技能中的“技能几率提升 M/S”强度作为占位结果
    help_bonus = has_helper_bonus(sub_skills)
    prob = get_skill_prob(sub_skills)
    help_speed = get_help_speed(sub_skills)
    # 兼容性格字段：資料表為「主技能」，OCR/界面可能為「主技能發動機率」
    if nature_up in ('主技能發動機率', '主技能'):
        nature_skill_prob = 2
    elif nature_down in ('主技能發動機率', '主技能'):
        nature_skill_prob = 0
    else:
        nature_skill_prob = 1
    # 读取效率数据
    efficient_data = pd.read_csv(os.path.join(EFFICIENT_DIR, 'Efficient_help_skill.csv'))
    # 根据prob, help_speed和nature_skill_prob筛选数据
    filtered_data = efficient_data[
            (efficient_data['help_bonus'] == int(help_bonus)) &
            (efficient_data['prob'] == prob) & 
            (efficient_data['help_speed'] == help_speed) & 
            (efficient_data['nature_skill_prob'] == nature_skill_prob)
        ]
    
    # 初始化默认值
    score = None
    result = None
    
    if filtered_data.empty:
        result = "宝可梦不可用"
    else:
        for j in filtered_data.itertuples():
            if nature_up == '幫忙速度':
                score = j.nature_help_up
                result = j.result1
            elif nature_down == '幫忙速度':
                score = j.nature_help_down
                result = j.result3
            else:
                score = j.nature_help_none
                result = j.result2
        if score is None:
            result = "宝可梦不可用"
    
    return score, result

def ingredient_type(sub_skills, nature_up, nature_down):
    """對食材型寶可夢進行計算"""
    # 使用副技能中的"食材几率提升 M/S"强度作为占位结果
    help_bonus = has_helper_bonus(sub_skills)
    prob = get_ingredient_prob(sub_skills)
    help_speed = get_help_speed(sub_skills)
    
    # 兼容性格字段：資料表為「食材發現」，OCR/界面可能為「食材發現率」
    if nature_up in ('食材發現率', '食材發現'):
        nature_ingredient_prob = 2
    elif nature_down in ('食材發現率', '食材發現'):
        nature_ingredient_prob = 0
    else:
        nature_ingredient_prob = 1
    # 读取效率数据
    efficient_data = pd.read_csv(os.path.join(EFFICIENT_DIR, 'Efficient_help_ingredient.csv'))
    # 根据prob, help_speed和nature_ingredient_prob筛选数据
    filtered_data = efficient_data[
            (efficient_data['help_bonus'] == int(help_bonus)) &
            (efficient_data['prob'] == prob) &
            (efficient_data['help_speed'] == help_speed) &
            (efficient_data['nature_ingredient_prob'] == nature_ingredient_prob)
        ]
    # 初始化默认值
    score = None
    result = None
    
    if filtered_data.empty:
        result = "宝可梦不可用"
    else:
        for j in filtered_data.itertuples():
            if nature_up == '幫忙速度':
                score = j.nature_help_up
                result = j.result1
            elif nature_down == '幫忙速度':
                score = j.nature_help_down
                result = j.result3
            else:
                score = j.nature_help_none
                result = j.result2
        if score is None:
            result = "宝可梦不可用"
    
    return score, result

def get_skill_prob(sub_skills):
    """
    计算副技能中的“技能几率提升”强度：
    - 有 M: +2
    - 有 S: +1
    - 两者都有: 3
    - 两者都没有: 0
    兼容繁/简与“幾/几/機率”，并考虑全角字母Ｍ/Ｓ。
    """
    if not sub_skills:
        return 0

    def has_level(level_char):
        # level_char: 'M' 或 'S'
        fullwidth = 'Ｍ' if level_char == 'M' else 'Ｓ'
        for t in sub_skills:
            if not isinstance(t, str):
                continue
            s = t.replace(' ', '')
            # 关键词片段：技能 + (幾率|機率) + 提升 + 等级（仅繁体）
            has_phrase = (
                ('技能幾率提升' in s) or
                ('技能機率提升' in s)
            )
            has_level_mark = (level_char in s) or (fullwidth in s)
            if has_phrase and has_level_mark:
                return True
        return False

    m = has_level('M')
    s = has_level('S')
    return (2 if m else 0) + (1 if s else 0)

def get_ingredient_prob(sub_skills):
    """
    计算副技能中的“食材几率提升”强度：
    - 有 M: +2
    - 有 S: +1
    - 两者都有: 3
    - 两者都没有: 0
    兼容繁/简与“幾/几/機率”，并考虑全角字母Ｍ/Ｓ。
    """
    if not sub_skills:
        return 0

    def has_level(level_char):
        fullwidth = 'Ｍ' if level_char == 'M' else 'Ｓ'
        for t in sub_skills:
            if not isinstance(t, str):
                continue
            s = t.replace(' ', '')
            # 关键词片段：食材 + (幾率|機率) + 提升 + 等级（仅繁体）
            has_phrase = (
                ('食材幾率提升' in s) or
                ('食材機率提升' in s)
            )
            has_level_mark = (level_char in s) or (fullwidth in s)
            if has_phrase and has_level_mark:
                return True
        return False

    m = has_level('M')
    s = has_level('S')
    return (2 if m else 0) + (1 if s else 0)

def get_help_speed(sub_skills):
    """
    计算副技能中的“幫忙速度”强度：
    - 有 M: +2
    - 有 S: +1
    - 两者都有: 3
    - 两者都没有: 0
    兼容繁/简（幫/帮）与全角字母Ｍ/Ｓ。
    """
    if not sub_skills:
        return 0

    def has_level(level_char):
        fullwidth = 'Ｍ' if level_char == 'M' else 'Ｓ'
        for t in sub_skills:
            if not isinstance(t, str):
                continue
            s = t.replace(' ', '')
            # 关键词片段：幫忙速度（仅繁体）
            has_phrase = ('幫忙速度' in s)
            has_level_mark = (level_char in s) or (fullwidth in s)
            if has_phrase and has_level_mark:
                return True
        return False

    m = has_level('M')
    s = has_level('S')
    return (2 if m else 0) + (1 if s else 0)


def calculator(
        pokemon_info, 
        nature_up,
        nature_down,
        sub_skills
    ):
    """主计算函数，根据是否有幫手獎勵调用相应方法"""
    ptype = get_pokemon_type(pokemon_info)
    if ptype == '樹果型':
        return fruit_type(sub_skills, nature_up, nature_down)
    elif ptype == '技能型':
        return skill_type(sub_skills, nature_up, nature_down)
    elif ptype == '食材型':
        return ingredient_type(sub_skills, nature_up, nature_down)
    else:
        raise ValueError(f"未知的类型: {ptype}")

