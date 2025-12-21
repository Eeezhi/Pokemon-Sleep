import os
import pandas as pd
import difflib
import numpy as np
import streamlit as st
#from google.cloud import bigquery as bq
#from google.oauth2 import service_account
from img_util.parse_img_v2 import TransformImage

# 创建 API 客户端（占位）：如果切换回 BigQuery，可解除顶部注释并使用 service_account/bq

category_list = ["全部", "點心/飲料", "沙拉", "咖哩/濃湯"]
curry_soup_list = [
    "特選蘋果咖哩",
    "炙燒尾肉咖哩",
    "太陽之力番茄咖哩",
    "絕對睡眠奶油咖哩",
    "辣味蔥勁十足咖哩",
    "蘑菇孢子咖哩",
    "親子愛咖哩",
    "吃飽飽起司肉排咖哩",
    "窩心白醬濃湯",
    "單純白醬濃湯",
    "豆製肉排咖哩",
    "寶寶甜蜜咖哩",
    "忍者咖哩",
    "日照炸肉排咖哩",
    "入口即化蛋捲咖哩",
    "健美豆子咖哩",
]
salad_list = [
    "呆呆獸尾巴的胡椒沙拉",
    "蘑菇孢子沙拉",
    "撥雪凱撒沙拉",
    "貪吃鬼洋芋沙拉",
    "濕潤豆腐沙拉",
    "蠻力豪邁沙拉",
    "豆製火腿沙拉",
    "好眠番茄沙拉",
    "哞哞起司番茄沙拉",
    "心情不定肉沙拉淋巧克力醬",
    "過熱沙拉",
    "特選蘋果沙拉",
    "免疫蔥花沙拉",
    "迷人蘋果起司沙拉",
    "忍者沙拉",
    "熱風豆腐沙拉",
]
snack_drink_list = [
    "熟成甜薯燒",
    "不屈薑餅",
    "特選蘋果汁",
    "手製勁爽汽水",
    "火花薑茶",
    "胖丁百匯布丁",
    "惡魔之吻水果牛奶",
    "祈願蘋果派",
    "橙夢的排毒茶",
    "甜甜香氣巧克力蛋糕",
    "哞哞熱鮮奶",
    "輕裝豆香蛋糕",
    "活力蛋白飲",
    "我行我素蔬菜汁",
    "大馬拉薩達",
    "大力士豆香甜甜圈",
]

all_recipe_dict = {
    "全部": ["全部"] + curry_soup_list + salad_list + snack_drink_list,
    "點心/飲料": ["全部"] + snack_drink_list,
    "沙拉": ["全部"] + salad_list,
    "咖哩/濃湯": ["全部"] + curry_soup_list,
}

show_cols = [
    "食譜",
    # '分類',
    # '食材1圖示',
    "食材1數量",
    # '食材2圖示',
    "食材2數量",
    # '食材3圖示',
    "食材3數量",
    # '食材4圖示',
    "食材4數量",
]


def get_ingredient_unique_list(df):
    ingredient_list = [
        *df["食材1"],
        *df["食材2"],
        *df["食材3"],
        *df["食材4"],
    ]
    ingredient_unique_list = list(set(ingredient_list))
    ingredient_unique_list = [i for i in ingredient_unique_list if i is not np.nan]
    return ingredient_unique_list


# 使用 st.cache_data 缓存：只有查询变化或超过 TTL 才会重新执行
@st.cache_data(ttl=600)  # 生存时间 (TTL) = 600 秒
def load_gsheet_data(sheets_url):
    csv_url = sheets_url.replace("/edit#gid=", "/export?format=csv&gid=")
    return pd.read_csv(csv_url, on_bad_lines="skip")


@st.cache_data
def get_can_cook(df, have_ingredients, match_mode):
    if not have_ingredients:
        return df

    index_match = []
    for row in df.itertuples():
        if match_mode == "任一食材符合":
            if any(i in row.all_food for i in have_ingredients):
                index_match.append(row.Index)
        else:
            if all(i in row.all_food for i in have_ingredients):
                index_match.append(row.Index)

    can_cook = df.iloc[index_match]
    return can_cook


def filter_category(df, category):
    return df.query(f"分類 == '{category}'") if category != "全部" else df


def filter_recipe(df, recipe):
    return df.query(f"食譜 == '{recipe}'") if recipe != "全部" else df

# -- 251204 Y.Huang
# @st.cache_data
# def get_pokemon_info_from_bq(pokemon):
#     sql = f"""
#         SELECT
#             p.* EXCEPT (_airbyte_raw_id,
#                 _airbyte_extracted_at,
#                 _airbyte_meta),
#             i.name AS ingredient,
#             i.energy AS ingredient_energy,
#             f.name AS fruit,
#             f.lv60_energy AS fruit_energy,
#             m.name AS main_skill,
#             m.Lv1,
#             m.Lv2,
#             m.Lv3,
#             m.Lv4,
#             m.Lv5,
#             m.Lv6,
#         FROM
#             `PokemonSleep.Pokemon` AS p
#         JOIN
#             `PokemonSleep.Ingredient` AS i
#         ON
#             i.name = p.ingredient
#         JOIN
#             `PokemonSleep.Fruit` AS f
#         ON
#             f.name = p.fruit
#         JOIN
#             `PokemonSleep.MainSkill` AS m
#         ON
#             m.name = p.main_skill
#         WHERE p.name = '{pokemon}'
#     """
#     credentials = service_account.Credentials.from_service_account_info(
#         st.secrets["gcp_service_account"]
#     )
#     client = bq.Client(credentials=credentials)
#     query_job = client.query(sql)
#     result_dict = [dict(result) for result in query_job][0]
#     return result_dict

# ++ 251204 Y.Huang 
#get_pokemon_info_from_bq重构为本地数据库版
UPPER_DIR = os.path.dirname(os.path.dirname(__file__)) 
BASE_DIR = os.path.dirname(UPPER_DIR)
DATA_DIR = os.path.join(BASE_DIR, "data")


df_ingredient = pd.read_csv(os.path.join(DATA_DIR, "Ingredient.csv"))
df_fruit = pd.read_csv(os.path.join(DATA_DIR, "Fruit.csv"))
df_skill = pd.read_csv(os.path.join(DATA_DIR, "MainSkill.csv"))

@st.cache_data
def get_pokemon_info_local(pokemon: str) -> dict | None:
    df_pokemon = pd.read_csv(os.path.join(DATA_DIR, "Pokemon.csv"))
    # 兼容不同欄位命名：去除列名空白並做別名映射
    df_pokemon.columns = [str(c).strip() for c in df_pokemon.columns]
    col_alias_map = {}
    if "ingredient" not in df_pokemon.columns:
        for alt in ("食材1", "食材", "食材一", "食材1名稱"):
            if alt in df_pokemon.columns:
                col_alias_map[alt] = "ingredient"
                break
    if "main_skill" not in df_pokemon.columns:
        for alt in ("技能", "主技能", "main skill"):
            if alt in df_pokemon.columns:
                col_alias_map[alt] = "main_skill"
                break
    if col_alias_map:
        df_pokemon = df_pokemon.rename(columns=col_alias_map)
    # Pokemon.csv 的列名是 "name"，不需要重命名
    # 防御性检查：缺少关键列时直接返回 None，避免 KeyError
    required_cols = {"name", "ingredient", "fruit", "main_skill"}
    if not required_cols.issubset(set(df_pokemon.columns)):
        missing = required_cols - set(df_pokemon.columns)
        st.warning(f"Pokemon.csv 缺少列: {', '.join(missing)}，請檢查資料格式")
        return None

    df = (
        df_pokemon
        .merge(df_ingredient, left_on="ingredient", right_on="name", suffixes=("", "_ingredient"))
        .merge(df_fruit, left_on="fruit", right_on="name", suffixes=("", "_fruit"))
        .merge(df_skill, left_on="main_skill", right_on="name", suffixes=("", "_skill"))
    )

    # 使用 "name" 列进行查询（找不到时尝试模糊匹配別名/近似名稱）
    subset = df[df["name"] == pokemon]
    if subset.empty:
        # 模糊匹配：在資料中尋找最接近的名稱（容忍 OCR 誤差如「撥/波」）
        name_list = df["name"].astype(str).tolist()
        candidates = difflib.get_close_matches(pokemon, name_list, n=1, cutoff=0.5)
        if candidates:
            subset = df[df["name"] == candidates[0]]
        else:
            return None

    row = subset.iloc[0].to_dict()

    # 将本地 CSV/合并的列名映射为 calculator 期望的鍵名
    def pick(*keys):
        for k in keys:
            if k in row and pd.notna(row[k]):
                return row[k]
        return None

    mapped = {}
    mapped['name'] = pick('name')
    mapped['final_evolution_step'] = pick('final_evolution_step', '最終進化階段')
    mapped['type'] = pick('type', '類型')
    mapped['fruit'] = pick('fruit')

    # fruit energy 可能在合并后的 fruit 表中以繁体中文列名存在
    mapped['fruit_energy'] = pick('fruit_energy', 'Lv60能量', 'lv60_energy')

    # ingredient 信息
    mapped['ingredient'] = pick('ingredient')
    mapped['ingredient_energy'] = pick('energy', 'energy_ingredient', 'ingredient_energy')
    mapped['ingredient_num'] = pick('食材1數量', 'ingredient_num', 'ingredient_1_num')

    # main skill
    mapped['main_skill'] = pick('main_skill')

    # 将可能存在的 Lv1..Lv6 等级列拷贝到映射中（供 calculator 读取）
    for i in range(1, 7):
        for candidate in (f'Lv{i}', f'Lv{i}_skill', f'Lv{i}_fruit', f'Lv{i}_ingredient'):
            if candidate in row:
                mapped[f'Lv{i}'] = row[candidate]
                break

    # 如果某些关键值还是 None，保留原始行中的其他字段以便排查
    # 合并原始 row（但 mapped 优先）
    combined = dict(row)
    combined.update(mapped)
    return combined

# @st.cache_data
# def get_item_list_from_bq(table_name):
#     sql = f"""
#         SELECT
#             DISTINCT(name)
#         FROM
#             `PokemonSleep.{table_name}`
#     """
#     credentials = service_account.Credentials.from_service_account_info(
#         st.secrets["gcp_service_account"]
#     )
#     client = bq.Client(credentials=credentials)
#     query_job = client.query(sql)
#     result_list = [result.values()[0] for result in query_job]
#     return result_list
#-- 251205 Y.Huang

#++ 251205 Y.Huang get_item_list_from_bq重构为本地数据库版
@st.cache_data
def get_item_list_from_bq(table_name: str) -> list[str]:
    """
    从本地 CSV 文件读取指定表的 name 列，并返回去重后的列表。
    """
    file_path = os.path.join(DATA_DIR, f"{table_name}.csv")

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"找不到文件: {file_path}")

    df = pd.read_csv(file_path)

    if "name" not in df.columns:
        raise ValueError(f"{table_name}.csv 缺少 'name' 列")

    # 去重并返回列表
    result_list: list[str] = list(df["name"].dropna().unique())
    return result_list

@st.cache_data
def get_nature_dict_from_bq(nature_name: str) -> dict:
    """
    本地 CSV 版本：依照性格名稱取得性格資訊（up、down）。
    期望 `data/Nature.csv` 包含欄位：`name`、`up`、`down`。
    回傳包含 `name`、`up`、`down` 的字典；若未命中則回傳 `up`/`down` 為 None 的預設字典。
    """
    csv_path = os.path.join(DATA_DIR, "Nature.csv")
    if not os.path.exists(csv_path):
        st.error(f"缺失文件: {csv_path}. 請將 Nature.csv 放入 data/ 目錄。")
        raise FileNotFoundError(f"Nature.csv not found in {DATA_DIR}")

    df = pd.read_csv(csv_path)
    if "name" not in df.columns:
        st.error(f"Nature.csv 必須包含 'name' 欄位")
        raise ValueError("Nature.csv missing 'name' column")

    matched = df[df["name"] == nature_name]
    # 回傳統一格式的字典，便於呼叫端處理：保證有 'name','up','down' 三個鍵
    result = {"name": nature_name, "up": None, "down": None}
    if matched.empty:
        # 回傳統一格式的字典，便於呼叫端處理
        return {"name": nature_name, "up": None, "down": None}

    row_dict = matched.iloc[0].to_dict()
    # 將可能缺少的鍵補上（若 CSV 中沒有 'up' 或 'down'，維持 None）
    result.update({k: row_dict.get(k, None) for k in ("up", "down")})
    # 若 CSV 有 name 欄位的正式名稱，使用它
    result["name"] = row_dict.get("name", nature_name)
    return result

@st.cache_data
def get_ingredient_dict_from_bq(ingredient: str) -> dict:
    """
    本地 CSV 版本：透過食材名稱從 `data/Ingredient.csv` 取得食材資料（至少包含 `name`、`energy`）。
    若找不到對應列，回傳預設的能量 0 以維持呼叫端行為一致。
    """
    # 使用预加载的 df_ingredient（文件在模块加载时读取）
    if "name" not in df_ingredient.columns:
        st.error("Ingredient.csv 缺少 'name' 欄位，請檢查 data/ 目錄中的檔案。")
        raise ValueError("Ingredient.csv missing 'name' column")

    matched = df_ingredient[df_ingredient["name"] == ingredient]
    if matched.empty:
        st.warning(f"Ingredient '{ingredient}' not found in Ingredient.csv")
        return {"name": ingredient, "energy": 0}

    return matched.iloc[0].to_dict()

# def get_rank_color_text(rank: str) -> str | None:
#     rank_color_dict = {
#         "SSS": f"評價: :rainbow[{rank}]",
#         "SS": f"評價: :rainbow[{rank}]",
#         "S": f"評價: :rainbow[{rank}]",
#         "A": f"評價: :red[{rank}]",
#         "B": f"評價: :violet[{rank}]",
#         "C": f"評價: :blue[{rank}]",
#         "D": f"評價: {rank}",
#         "E": f"評價: {rank}",
#     }
#     return rank_color_dict.get(rank)


# os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = st.secrets['bq_credentials_filepath']
# client = bq.Client()
# get_nature_dict_from_bq(client, '認真')


@st.cache_data(max_entries=3)
def process_img(img: bytes) -> dict:
    transform_img = TransformImage(img)
    info = transform_img.run()
    return info
