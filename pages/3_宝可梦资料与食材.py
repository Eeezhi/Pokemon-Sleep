import os
import streamlit as st
import pandas as pd
import numpy as np
from filepath import database_path

st.set_page_config(page_title='Pokemon Sleep App', layout="wide")
st.title('Pokemon Sleep 寶可夢')
st.caption('寶可夢 ＆ 食材、樹果')

#這裡的pokemon_transformed.csv是來源於下方url的Google試算表，經過轉換後的版本
#https://docs.google.com/spreadsheets/d/18aAHjg762T29F74yo8axDVFO09swCa7nUp_eTZ51ZAc/edit?gid=1273913201#gid=1273913201
POKEMON_TRANSFORMED = os.path.join(database_path, 'transformed/pokemon_transformed.csv')
df = pd.read_csv(POKEMON_TRANSFORMED, encoding='utf-8-sig')

# 兼容 transformed CSV 的欄位：把英文欄位映射為頁面使用的中文欄位
rename_map = {}
if 'name' in df.columns and '名稱' not in df.columns:
    rename_map['name'] = '名稱'
if 'fruit' in df.columns and '樹果' not in df.columns:
    rename_map['fruit'] = '樹果'
if 'all_ingredients' in df.columns and 'all_ingredients' not in df.columns:
    # 保持原名，用於查詢
    pass
if rename_map:
    df = df.rename(columns=rename_map)

ingredient_unique_list = list(set([*df['基本食材'], *df['Lv30食材'], *df['Lv60食材']]))
ingredient_unique_list = ['全部'] + [i for i in ingredient_unique_list if i is not np.nan]
fruit_unique_list = df['樹果'].unique()
fruit_unique_list = ['全部'] + [i for i in fruit_unique_list if i is not np.nan]

selected_ingredient = st.selectbox('食材', ingredient_unique_list)
# selected_fruit = st.selectbox('樹果', fruit_unique_list)

def query_ingredient(df):
    if selected_ingredient != '全部':
        index_match = []
        for row in df.itertuples():
            if row.all_ingredients is not np.nan:
                if selected_ingredient in row.all_ingredients:
                    index_match.append(row.Index)
        return df.iloc[index_match]
    else:
        return df
    
# def query_fruit(df):
#     if selected_fruit != '全部':
#         match_list = []
#         for row in df.itertuples():
#             if selected_fruit == row.fruit:
#                 match_list.append(row)
#         return pd.DataFrame(match_list)
#     else:
#         return df

match_df = df.pipe(query_ingredient)
# match_df = match_df.pipe(query_fruit)

match_df.set_index('名稱', inplace=True, drop=True)
cols = [
    '樹果',
    '基本食材',
    'Lv30食材',
    'Lv60食材',
    '來源島嶼',
    '睡眠類型'
]
match_df = match_df[cols]
match_df.fillna('', inplace=True)

def color_ingredients(val):
    color = '#ffff99'
    if val is not np.nan and selected_ingredient == val:
        return f'background-color: {color}'

st.dataframe(
    match_df.style.applymap(color_ingredients),
    width="stretch"
)
