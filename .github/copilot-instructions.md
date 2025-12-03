## 目的
给 AI 编码代理快速上手本仓库的实用说明 —— 包含架构、关键工作流、项目约定与常见坑。

## 一句俯瞰
本项目是以 Streamlit 为前端的工具（多页应用），负责：上传宝可梦截图 -> OCR 提取文字 -> 用本地数据或 BigQuery 得到宝可梦/食材信息 -> 计算并展示“能量/潜力”评分。

## 关键目录与文件
- `Home.py`：入口页，负责导航到三个子页面（位于 `pages/`）。
- `pages/1_宝可梦潜力计算器.py`：主流程示例（图片上传、调用 OCR、展示表单并调用计算器）。
- `pages/2_食材与料理食谱.py`、`pages/3_宝可梦資料與食材.py`：数据展示/筛选界面。
- `pages/util/util.py`：大量业务辅助函数（包含 `process_img`、本地 CSV 数据加载与 BigQuery 调用模板）。
- `img_util/parse_img.py`：OCR 逻辑（使用 `PaddleOCR`），并从 MongoDB 拉取可选项用于比对。
- `img_util/calculator.py`：核心“能量 / rank” 算法实现。
- `data/`：本地 CSV 作为 BigQuery 的本地替代（`Pokemon.csv`, `Ingredient.csv`, `Fruit.csv`, `MainSkill.csv` 等）。
- `notebook/`：用于调试 OCR 与 ETL 的笔记本（可参照运行和示例）。

## 数据与运行时依赖（注意点）
- OCR：优先使用 `PaddleOCR`（仓库 README 指明已采纳）。首次运行会下载 model，可能较慢。
- 系统包：`packages.txt` 列出部署时需在容器中安装的系统依赖（例如 `tesseract-ocr`、`libgl1-mesa-glx`）。
- Python 包：查看 `requirements.txt`，在本地用 Conda/venv 安装同版本依赖。
- Secrets：
  - GCP：`st.secrets["gcp_service_account"]`（BigQuery 客户端示例在 `pages/...` 和 `pages/util/util.py` 中被注释/部分使用）。
  - MongoDB：`st.secrets["db_username"]` / `st.secrets["db_password"]`（在 `img_util/parse_img.py` 中用于拉取 item 列表）。

## 典型本地启动 / 调试命令
（请在激活 Python 环境并安装 `requirements.txt` 后执行）
```bash
# 在项目根目录
pip install -r requirements.txt
streamlit run Home.py
```
调试 OCR 时，可在 `notebook/` 里打开相应 Notebook（`OCR_paddleOCR.ipynb` / `OCR_EasyOCR.ipynb`）直接跑示例。

## 项目特有约定与模式（重要）
- 多页 Streamlit：每个页面文件放在 `pages/`，文件名使用中文 + 序号（因此引用/修改时注意文件名编码）。
- 双路径数据源：代码保留了 BigQuery 查询版本（注释）和本地 CSV 回退实现（`get_pokemon_info_local`），修改数据源时需同步两处逻辑。
- OCR -> 比对：`img_util/parse_img.py` 使用 PaddleOCR 输出，再用 MongoDB 中从 Airbyte 导入的集合 `_airbyte_data._id` 列表做字符串比对（因此 OCR 输出和数据库中条目的一致性非常重要）。
- 缓存：Streamlit 使用 `@st.cache_data` 装饰器缓存结果（如 `process_img`, `get_pokemon_info_local` 等）。编辑这些函数后需注意缓存失效或在页面刷新时清除缓存以避免旧数据影响。
- UI/UX：Streamlit 使用 `st.status`, `st.form`, `st.link_button`等组件，更新状态要使用 `status.update(...)` 来给用户反馈。

## 常见改动点与实施建议
- 要修改评分逻辑：编辑 `img_util/calculator.py`，在本地运行 `pages/1_宝可梦潜力计算器.py` 做端到端验收。
- 要修改 OCR 解析规则：编辑 `img_util/parse_img.py` 的 `filter_text`，注意 `pokemons_list` / `*_list` 是在模块导入时从 MongoDB 读取的（非实时），有时需要重启 Streamlit 服务以加载新的列表。
- 切换到 BigQuery：打开 `pages/util/util.py` 中被注释的 BigQuery 查询，确保 `st.secrets` 中有 GCP 凭据，并且项目/表名与 SQL 匹配。

## 部署注意事项
- Docker / 部署镜像需包含 `packages.txt` 中的系统依赖（PaddleOCR 与 Tesseract 的本地运行依赖）。
- PaddleOCR 首次运行会下载模型，建议在镜像构建或首次启动时做好缓存策略以减少冷启动时间。

## 调试提示与陷阱
- OCR 首次失败常见原因：图像方向、中文繁体/简体设定、模型未下载、MongoDB 列表与 OCR 输出大小写/字符差异。
- 编辑与调试缓存后可通过在 UI 中强制重启 Streamlit 或清除缓存来确认变更。

如果你希望我把本说明中的某部分细化为可执行的脚本（比如：部署 Dockerfile、Streamlit run wrapper、或一个 CI 验证脚本），告诉我你想先解决哪一项或把哪个场景自动化。请审阅上述内容并指出需要补充或不准确的地方。
