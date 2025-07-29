import streamlit as st
import pandas as pd
import pytesseract
from PIL import Image

st.set_page_config(page_title="NailVesta 入库程序", layout="wide")
st.title("💅 NailVesta 入库程序")
st.caption("上传截图和库存 CSV 文件，自动生成可复制的入库数量")

# Windows 用户请取消注释以下行并设置 tesseract 路径
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# 上传截图图片
image_file = st.file_uploader("📸 上传入库截图（含 SKU + S/M/L 数量）", type=["png", "jpg", "jpeg"])

# 上传库存表
csv_file = st.file_uploader("📄 上传库存表格（CSV 格式，SKU 在第3列）", type=["csv"])

if image_file and csv_file:
    try:
        # 加载图片和库存表
        image = Image.open(image_file)
        stock_df = pd.read_csv(csv_file)
        stock_skus = stock_df.iloc[:, 2].dropna().astype(str).tolist()

        # OCR识别
        raw_text = pytesseract.image_to_string(image, config='--oem 3 --psm 6')
        lines = [line for line in raw_text.split('\n') if line.strip()]

        # 提取基础 SKU 和 S/M/L 数量，构建 SKU 尺码键值对
        entry_map = {}
        for line in lines:
            parts = line.split()
            if len(parts) >= 11:
                base_sku = parts[2]
                try:
                    s = int(parts[8])
                    m = int(parts[9])
                    l = int(parts[10])
                    entry_map[f"{base_sku}-S"] = s
                    entry_map[f"{base_sku}-M"] = m
                    entry_map[f"{base_sku}-L"] = l
                except ValueError:
                    continue

        # 生成入库数量列
        output_quantities = []
        unmatched_skus = []

        for sku in stock_skus:
            if sku in entry_map:
                output_quantities.append(entry_map[sku])
            else:
                output_quantities.append("")
                unmatched_skus.append(sku)

        result_df = pd.DataFrame({
            "SKU": stock_skus,
            "入库数量": output_quantities
        })

        st.success("✅ 入库数量已生成，按库存表 SKU 顺序排列")
        st.dataframe(result_df, use_container_width=True)

        st.download_button(
            label="📥 下载结果 CSV",
            data=result_df.to_csv(index=False).encode("utf-8-sig"),
            file_name="入库数量对照表.csv",
            mime="text/csv"
        )

        # 可复制粘贴的数量列
        st.markdown("### 📋 可复制的入库数量列")
        st.code("\n".join([str(i) for i in output_quantities if str(i).strip() != ""]), language="text")

        if unmatched_skus:
            st.warning(f"⚠️ 有 {len(unmatched_skus)} 个 SKU 无法匹配入库表，示例：")
            st.text("\n".join(unmatched_skus[:10]))

    except Exception as e:
        st.error(f"❌ 出错啦：{e}")
