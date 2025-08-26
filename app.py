import streamlit as st
import pandas as pd
import pdfplumber

st.set_page_config(page_title="NailVesta 入库匹配工具", layout="wide")
st.title("💅 NailVesta 入库匹配工具（支持 PDF 入库表）")

# 上传文件
stock_file = st.file_uploader("📦 上传库存表（含『SKU编码』列，形如 NPX014-S）", type=["csv","xlsx"])
entry_file = st.file_uploader("📝 上传入库表（支持 CSV/XLSX/PDF，需含『SKU 编码』『S数量』『M数量』『L数量』）", type=["csv","xlsx","pdf"])

# 读取函数
def read_file(file):
    if file.name.endswith(".csv"):
        return pd.read_csv(file, encoding="utf-8-sig")
    elif file.name.endswith(".xlsx"):
        return pd.read_excel(file)
    elif file.name.endswith(".pdf"):
        tables = []
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                table = page.extract_table()
                if table:
                    tables.extend(table)
        df = pd.DataFrame(tables[1:], columns=tables[0])  # 第一行当表头
        return df
    else:
        raise ValueError("不支持的文件格式")

if stock_file and entry_file:
    try:
        stock_df = read_file(stock_file)
        entry_df = read_file(entry_file)

        # 库存表校验
        if "SKU编码" not in stock_df.columns:
            st.error("❌ 库存表缺少『SKU编码』列。")
            st.stop()

        stock_skus = stock_df["SKU编码"].dropna().astype(str).str.strip().tolist()

        # 入库映射
        entry_map = {}
        for _, row in entry_df.iterrows():
            if "SKU 编码" not in entry_df.columns:
                st.error("❌ 入库表缺少『SKU 编码』列。")
                st.stop()
            base_sku = str(row["SKU 编码"]).strip()
            for size, col in zip(["S", "M", "L"], ["S数量", "M数量", "L数量"]):
                if col in entry_df.columns:
                    qty = pd.to_numeric(row[col], errors="coerce")
                    if not pd.isna(qty) and qty > 0:
                        full_sku = f"{base_sku}-{size}"
                        entry_map[full_sku] = entry_map.get(full_sku, 0) + int(qty)

        # 匹配结果
        results, unmatched = [], []
        for sku in stock_skus:
            qty = entry_map.get(sku, "")
            results.append((sku, qty))
            if qty == "":
                unmatched.append(sku)

        result_df = pd.DataFrame(results, columns=["SKU编码", "入库数量"])

        st.success("✅ 匹配完成！")
        st.dataframe(result_df, use_container_width=True)

        st.download_button(
            "📥 下载入库数量 CSV",
            result_df.to_csv(index=False).encode("utf-8-sig"),
            "NailVesta_入库数量.csv",
            "text/csv"
        )

        if unmatched:
            st.warning(f"⚠️ 有 {len(unmatched)} 个 SKU 未匹配，示例：\n" + "\n".join(unmatched[:10]))

    except Exception as e:
        st.error(f"❌ 出错：{e}")
