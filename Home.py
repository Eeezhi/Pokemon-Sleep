import streamlit as st
from PIL import Image
from img.img_filepath import POKEMON_SLEEP_IMG
from streamlit.components.v1 import html


class Pages:
    base_url = "http://localhost:8501/" #本地调试
    calculator = base_url + "宝可梦潜力计算器"
    recipe = base_url + "食材与料理食谱"
    pokemon_info = base_url + "宝可梦资料与食材"


st.title("Pokemon Sleep 小幫手首頁")

image = Image.open(POKEMON_SLEEP_IMG)
st.image(image, use_container_width=True, output_format="png")

col1, col2, col3 = st.columns(3)
with col1:
    image1 = Image.open("img/calculator.jpeg")
    image1 = image1.resize((600, 500))
    st.image(image1)
    st.link_button("宝可梦潜力计算器", Pages.calculator, type="primary", use_container_width=True)
with col2:
    image1 = Image.open("img/recipe.png")
    image1 = image1.resize((600, 500))
    st.image(image1)
    st.link_button("食材与料理食谱", Pages.recipe, type="primary", use_container_width=True)
with col3:
    image1 = Image.open("img/pokemon.png")
    image1 = image1.resize((600, 500))
    st.image(image1)
    st.link_button("宝可梦资料与食材", Pages.pokemon_info, type="primary", use_container_width=True)
