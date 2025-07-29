import streamlit as st
import pandas as pd
import pdfplumber

st.set_page_config(page_title="NailVesta 入库程序", layout="wide")
st.title("NailVesta 入库程序")

# 上传库存文件
inventory_file = st.file_uploader("📤 上传 NailVesta 产品库存表（CSV 格式）", type=["csv"])

# 下载说明 PDF
st.markdown("### 📄 入库表填写说明")
with open("entry_upload_example.pdf", "rb") as f:
    st.download_button(
        label="📥 下载入库表填写示意 PDF",
        data=f,
        file_name="entry_upload_example.pdf",
        mime="application/pdf"
    )

# 上传入库 PDF 文件
st.markdown("### 📤 上传入库表（PDF 格式）")
entry_file = st.file_uploader("上传入库 PDF 文件以预览内容", type=["pdf"])

# PDF 内容预览
if entry_file:
    try:
        with pdfplumber.open(entry_file) as pdf:
            text = ""
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        st.markdown("#### 📝 PDF 内容预览")
        st.text_area("PDF 中提取的文本内容", text.strip(), height=400)
    except Exception as e:
        st.error(f"❌ PDF 解析失败：{e}")

# 库存表预览
if inventory_file:
    try:
        inventory_df = pd.read_csv(inventory_file)
        inventory_df = inventory_df.dropna(subset=['SKU编码'])
        st.markdown("### 📦 产品库存预览（前 10 行）")
        st.dataframe(inventory_df.head(10))
    except Exception as e:
        st.error(f"❌ 读取库存 CSV 文件失败：{e}")
