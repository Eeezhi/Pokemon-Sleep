import os
import streamlit as st
import pandas as pd
from PIL import Image
from filepath import img_path, database_path
#from google.cloud import bigquery as bq
#from google.oauth2 import service_account

st.set_page_config(page_title="Pokemon Sleep App", layout="wide")
st.title("Pokemon Sleep 宝可梦潜力计算器")
st.caption("上传宝可梦的截图，自动获取图片信息，并可一键计算潜力评价")
#st.caption("- 2024/02/01 更新最新宝可梦，包含童偶熊、拉鲁拉丝、迷你龙")
st.caption("- 计算方法出处：小红书@谜之玩家Leo，《宝可梦效率速查表》")

uploaded_file = st.file_uploader("上传截图", type=["jpg", "png"])
st.divider()

if uploaded_file is not None:
    # 使用 parse_img_v2.py 的 TransformImage 来解析图片（支持表格识别）
    from img_util.parse_img_v2 import TransformImage
    
    img = uploaded_file.getvalue()
    transformer = TransformImage(img)
    info = transformer.run()  # 返回解析后的字典：{'pokemon': ..., 'main_skill': ..., 'sub_skill_1': ..., 'nature': ...}

    # 顯示圖片（缩小显示）
    # st.header('上傳的圖片')
    # 将图片宽度限制为 400px（可按需调整为更小或更大），或使用 use_column_width=True 以自适应列宽
    st.image(Image.open(uploaded_file), width=400)

    if info.get("pokemon"):
        from pages.util.util import (
            #get_pokemon_info_from_bq,
            get_pokemon_info_local,
            get_item_list_from_bq,
            get_nature_dict_from_bq,
            get_ingredient_dict_from_bq,
        )

        # Pokemon
        #pokemon_info = get_pokemon_info_from_bq(info["pokemon"])
        pokemon_info = get_pokemon_info_local(info["pokemon"])
        
        # 检查是否找到了宝可梦信息
        if pokemon_info is None:
            st.error(f"❌ 找不到宝可梦 '{info['pokemon']}' 的信息，请检查数据库")
        else:
            # Sub Skills
            sub_skills_list = get_item_list_from_bq("SubSkill")
            sub_skills_list = sorted(sub_skills_list)
            sub_skills_list.insert(0, "---")
            
            sub_skill_1 = st.text_input("副技能1", value=info.get('sub_skill_1', ''))
            sub_skill_2 = st.text_input("副技能2", value=info.get('sub_skill_2', ''))
            sub_skill_3 = st.text_input("副技能3", value=info.get('sub_skill_3', ''))
            sub_skill_4 = st.text_input("副技能4", value=info.get('sub_skill_4', ''))
            sub_skill_5 = st.text_input("副技能5", value=info.get('sub_skill_5', ''))

            sub_skills = [sub_skill_1, sub_skill_2, sub_skill_3, sub_skill_4, sub_skill_5]
            sub_skills_for_calc = [sub_skill_1, sub_skill_2, sub_skill_3]

            # Ingredient 2 and 3
            ingredient_list = get_item_list_from_bq("Ingredient")
            ingredient_list.insert(0, "---")
            ingredient_2 = st.selectbox(
                ":orange[食材2]", ingredient_list, index=ingredient_list.index(pokemon_info['ingredient'])
            )
            ingredient_2_num = st.slider(
                ":orange[食材2數量]", value=2, min_value=1, max_value=10, step=1
            )

            ingredient_3 = st.selectbox(
                ":orange[食材3]", ingredient_list, index=ingredient_list.index(pokemon_info['ingredient'])
            )
            ingredient_3_num = st.slider(
                ":orange[食材3數量]", value=4, min_value=1, max_value=10, step=1
            )

            # Nature
            nature = st.text_input("性格", value=f"{info.get('nature', '')}")
            if nature:
                nature_data = get_nature_dict_from_bq(nature)
                nature_up = nature_data["up"] if nature_data["up"] else '無性格效果'
                nature_down = nature_data["down"] if nature_data["down"] else '無性格效果'
                st.write(":small_red_triangle: UP: ", nature_up)
                st.write(":small_blue_diamond: DOWN: ", nature_down)
            
            st.divider()
            
            # 自动计算并在状态框中显示结果
            if nature:
                with st.status("识别完成！", state="complete", expanded=True) as calc_status:
                    from img_util.new_calc import calculator
                    ingredient_2_energy = get_ingredient_dict_from_bq(ingredient_2)['energy']
                    ingredient_3_energy = get_ingredient_dict_from_bq(ingredient_3)['energy']
                    info_dict = {
                        'pokemon_info': pokemon_info,
                        'nature_up': nature_up,
                        'nature_down': nature_down,
                        'sub_skills': sub_skills_for_calc,
                        # 'ingredient_2_num': int(ingredient_2_num),
                        # 'ingredient_2_energy': int(ingredient_2_energy),
                        # 'ingredient_3_num': int(ingredient_3_num),
                        # 'ingredient_3_energy': int(ingredient_3_energy),
                    }

                    with st.expander("提取到的信息", expanded=False):
                        st.json({
                            '寶可夢名稱': pokemon_info['name'],
                            '寶可夢類型': pokemon_info['type'],
                            '主技能': pokemon_info['main_skill'],
                            '副技能列表': sub_skills,
                            '性格': nature,
                            '性格加成': nature_up,
                            '性格減少': nature_down
                        })

                    score, result = calculator(**info_dict)
                    if pd.notna(score):
                        st.markdown(f"### 宝可梦效率：**{score}**")
                        st.markdown(f"### 评价结果：**{result}**")
                    else:
                        st.markdown(f"### 评价结果：**{result}**")
            
            st.divider()
            
            # # 顯示擷取結果到文字輸入框
            # st.header("OCR识别文本")
            # show_info = {
            #     'pokemon': '寶可夢',
            #     'fruit': '樹果',
            #     'ingredient': '食材 1',
            #     'main_skill': '主技能',
            # }
            # for k, v in pokemon_info.items():
            #     if k in show_info.keys():
            #         k_zhtw = show_info.get(k)
            #         st.markdown(f'- **{k_zhtw}**: {v}')
    else:
        st.warning("⚠️ 无法识别宝可梦名稱，请上传更清晰的截圖")

else:
    st.header("截图示例")
    st.write("左上角宝可梦方框刚好「遮住第一个食材」，并且最底部刚好出现「性格」")
    example_img = os.path.join(img_path, "example.PNG")
    st.image(example_img ,width=400) #缩小显示