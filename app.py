import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="NailVesta 入库程序", layout="wide")
st.title("💅 NailVesta 入库程序（清洗版）")

# 文件上传
stock_file = st.file_uploader("📦 上传库存表（SKU 在某列）", type=["csv", "xlsx"])
entry_file = st.file_uploader("📝 上传入库表（SKU 样式名在第3列，S/M/L 在第9/10/11列）", type=["csv", "xlsx"])

# 文件读取函数
def read_file(file):
    if file.name.endswith("csv"):
        return pd.read_csv(file)
    else:
        return pd.read_excel(file)

# SKU 识别函数
def is_valid_sku(s):
    return isinstance(s, str) and re.match(r"^[A-Z]{2,3}[A-Z]?\d{3}$", s)

if stock_file and entry_file:
    try:
        stock_df = read_file(stock_file)
        entry_df = read_file(entry_file)

        # Step 1: 提取库存中的有效 SKU 列（自动识别）
        sku_column = None
        for col in stock_df.columns:
            if stock_df[col].apply(is_valid_sku).sum() > 5:  # 至少匹配5个才算合理
                sku_column = col
                break

        if sku_column is None:
            st.error("❌ 没有找到有效的 SKU 列（如 NPJ005 格式），请检查库存表格式")
        else:
            stock_skus = stock_df[sku_column].dropna().astype(str)
            stock_skus = [sku for sku in stock_skus if is_valid_sku(sku)]

            # Step 2: 构造入库 SKU → 数量映射（用样式名+尺码）
            entry_map = {}
            for _, row in entry_df.iterrows():
                try:
                    base = str(row.iloc[2]).strip()
                    s = int(row.iloc[8])
                    m = int(row.iloc[9])
                    l = int(row.iloc[10])
                    entry_map[f"{base}-S"] = s
                    entry_map[f"{base}-M"] = m
                    entry_map[f"{base}-L"] = l
                except:
                    continue

            # Step 3: 匹配生成结果（未匹配设为空）
            result_skus = []
            result_qtys = []
            unmatched = []

            for sku in stock_skus:
                if sku in entry_map:
                    result_skus.append(sku)
                    result_qtys.append(entry_map[sku])
                else:
                    result_skus.append(sku)
                    result_qtys.append("")
                    unmatched.append(sku)

            result_df = pd.DataFrame({
                "SKU": result_skus,
                "入库数量": result_qtys
            })

            st.success("✅ 入库数量匹配完成")
            st.dataframe(result_df, use_container_width=True)

            st.markdown("### 📋 可复制的入库数量")
            st.code("\n".join([str(i) for i in result_qtys if str(i).strip() != ""]), language="text")

            st.download_button(
                label="📥 下载 CSV",
                data=result_df.to_csv(index=False).encode("utf-8-sig"),
                file_name="入库匹配结果.csv",
                mime="text/csv"
            )

            if unmatched:
                st.warning(f"⚠️ 共 {len(unmatched)} 个 SKU 未匹配，示例：")
                st.text("\n".join(unmatched[:10]))

    except Exception as e:
        st.error(f"❌ 出错了：{e}")
