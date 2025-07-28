import streamlit as st
import pandas as pd
import numpy as np
import pdfplumber

st.title("NailVesta 入库程序")

# 上传库存文件
inventory_file = st.file_uploader("上传 NailVesta 产品库存表", type=["csv"])

# 展示 PDF 示例文件（说明示意）
st.markdown("### 📄 入库表填写说明")
with open("entry_upload_example.pdf", "rb") as f:
    st.download_button(
        label="📥 下载入库表填写示意 PDF",
        data=f,
        file_name="entry_upload_example.pdf",
        mime="application/pdf"
    )

# 上传入库表 PDF
st.markdown("### 上传入库表（PDF 格式）")
entry_file = st.file_uploader("上传入库表 PDF", type=["pdf"])

if entry_file:
    try:
        with pdfplumber.open(entry_file) as pdf:
            full_text = ""
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    full_text += page_text + "\n"
        st.markdown("#### 📖 入库表内容预览")
        st.text_area("入库表文本内容", full_text, height=400)
    except Exception as e:
        st.error(f"PDF 解析失败：{e}")

# 以下逻辑只处理库存 CSV 表
if inventory_file:
    try:
        inventory_df = pd.read_csv(inventory_file)
        inventory_df = inventory_df.dropna(subset=['SKU编码'])

        st.markdown("### 📦 当前库存 SKU 列表（前 10 行）")
        st.dataframe(inventory_df.head(10))
        st.info("⚠️ 当前程序版本仅展示库存与 PDF 入库内容，尚未实现自动匹配 PDF 中的 SKU 与入库数量。")
    except Exception as e:
        st.error(f"读取库存表出错：{e}")
