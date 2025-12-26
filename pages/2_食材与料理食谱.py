import streamlit as st
import pandas as pd
import numpy as np
import os
from filepath import database_path

from pages.util.util import (
    get_ingredient_unique_list,
    get_can_cook,
    category_list,
    all_recipe_dict,
    filter_category,
    filter_recipe,
    show_cols
)

st.set_page_config(page_title='Pokemon Sleep App', layout="wide")
st.title('Pokemon Sleep 食谱')
st.caption('利用现在有的食材，查询可以料理的食谱')

RECIPE_TRANSFORMED = os.path.join(database_path, 'transformed/recipe_transformed.csv')
df = pd.read_csv(RECIPE_TRANSFORMED, index_col=0, encoding='utf-8-sig')
ingredient_unique_list = get_ingredient_unique_list(df)

ingredient_col, match_mode_col = st.columns([2, 1])
with ingredient_col:
    have_ingredients = st.multiselect(
        '食材', 
        ingredient_unique_list,
        placeholder='请选择食材（可多选）'
    )
with match_mode_col:
    # match_mode = st.checkbox('任一食材符合', False)
    match_mode = st.radio('筛选方式', ['所有食材符合', '任一食材符合'], 0)
category_col, recipe_col = st.columns(2)
with category_col:
    category = st.selectbox('食谱分类', category_list)
with recipe_col:
    recipe = st.selectbox('食谱名称', all_recipe_dict.get(category, all_recipe_dict['全部']))

st.divider()

ingredients_str_list = ', '.join(have_ingredients) if have_ingredients else '全部'
st.write(f"目前选择的食材:")
st.info(f"{ingredients_str_list}")

can_cook = get_can_cook(df, have_ingredients, match_mode)
can_cook_filtered = (
    can_cook
    .pipe(filter_category, category)
    .pipe(filter_recipe, recipe)
)

def color_ingredients(val):
    color = '#ffff99'
    if val is not np.nan and any(i in val for i in have_ingredients):
        return f'background-color: {color}'

st.write(f"可料理食谱:")
can_cook_filtered = can_cook_filtered[show_cols].set_index('食譜').T
can_cook_filtered = can_cook_filtered.fillna('')
st.dataframe(can_cook_filtered.style.applymap(color_ingredients))
