# Pokemon-Sleep Helper

![pokemon_sleep](img/pokemon_sleep.png)

## Try it
https://eeezhisalt.top/pokemonsleep/

## Latest Updates
- 2025/12/20更新
 - 宝可梦的元数据从Google Sheet/Airbyte/BigQuery变成了本地csv文件，方便自己添加
 - ocr组件从本地的paddleocr/easyocr变成了free ocr api，低功耗嵌入式等网站服务器也可以运行

## 目前功能

左側欄共有4個頁面

1. [Home](https://pokemon-sleep.streamlit.app): 首頁，點擊紅色按鈕進入不同頁面
2. [潛力計算機](https://pokemon-sleep.streamlit.app/%E6%BD%9B%E5%8A%9B%E8%A8%88%E7%AE%97%E6%A9%9F): 上傳遊戲中的寶可夢截圖，自動辨識所有文字，並可計算潛力
3. [Recipe](https://pokemon-sleep.streamlit.app/Recipe): 利用自己現有的食材篩選能做出哪些食譜料理
4. [Pokemon](https://pokemon-sleep.streamlit.app/Pokemon): 寶可夢的樹果、食材、來源島嶼

## 使用技術
- Streamlit (Front-end GUI)
- Python
  - Data process: `numpy`, `pandas`
  - Crawler: `requests`, `BeautifulSoup`, `fake_useragent`
- Docker (Container)
- VS Code (IDE)

## TODO
- [ ] 将图鉴从2024年版本更新至最新版本

## 資料來源

- [《野兔小幫手》v1.3.0 (Google Sheet)](https://docs.google.com/spreadsheets/d/18aAHjg762T29F74yo8axDVFO09swCa7nUp_eTZ51ZAc/edit#gid=439534137)
- [寶可夢全食譜彙整一覽表](https://pinogamer.com/16427)
- [【攻略】使用能量計算!!更科學的『寶可夢Sleep潛力計算機v4.5』五段評價系統!!](https://forum.gamer.com.tw/C.php?bsn=36685&snA=913&tnum=354)


## Note
- Streamlit Dataframe 同一個欄位的資料不能混合圖片和文字
- 使用 SHAP 要注意其他套件的版本（參考 `requirements.txt` 檔案）

