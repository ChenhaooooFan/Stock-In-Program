import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="NailVesta 入库程序", layout="wide")
st.title("💅 NailVesta 入库程序（基于 SKU 编码精准匹配）")

# 上传文件
stock_file = st.file_uploader("📦 上传库存表（必须包含列名为『SKU编码』）", type=["csv", "xlsx"])
entry_file = st.file_uploader("📝 上传入库表（SKU 编码在第 4 列，S/M/L 在第 9/10/11 列）", type=["csv", "xlsx"])

# 文件读取函数
def read_file(file):
    if file.name.endswith(".csv"):
        return pd.read_csv(file)
    else:
        return pd.read_excel(file)

# SKU 格式校验函数（如 NPJ005）
def is_valid_sku(s):
    return isinstance(s, str) and re.fullmatch(r"[A-Z]{2,4}\d{3}", s)

if stock_file and entry_file:
    try:
        # 加载数据
        stock_df = read_file(stock_file)
        entry_df = read_file(entry_file)

        # 验证 SKU 编码列是否存在
        if "SKU编码" not in stock_df.columns:
            st.error("❌ 未找到『SKU编码』列，请检查库存表格式。")
            st.stop()

        # 提取库存 SKU（已带 -S/-M/-L 尾缀）
        stock_skus = stock_df["SKU编码"].dropna().astype(str).str.strip().tolist()

        # 构建入库 SKU → 数量 映射（从第 4 列提取 SKU 编码）
        entry_map = {}
        for _, row in entry_df.iterrows():
            try:
                base_sku = str(row.iloc[3]).strip()
                for size, col in zip(["S", "M", "L"], [8, 9, 10]):
                    qty = row.iloc[col]
                    if pd.notna(qty):
                        full_sku = f"{base_sku}-{size}"
                        entry_map[full_sku] = int(qty)
            except:
                continue

        # 对照生成匹配结果
        results = []
        unmatched = []

        for sku in stock_skus:
            qty = entry_map.get(sku, "")
            results.append((sku, qty))
            if qty == "":
                unmatched.append(sku)

        result_df = pd.DataFrame(results, columns=["SKU", "入库数量"])

        st.success("✅ 入库匹配成功！")
        st.dataframe(result_df, use_container_width=True)

        st.markdown("### 📋 可复制入库数量列")
        st.code("\n".join([str(q) for _, q in results if str(q).strip() != ""]), language="text")

        st.download_button(
            label="📥 下载匹配结果 CSV",
            data=result_df.to_csv(index=False).encode("utf-8-sig"),
            file_name="NailVesta_入库匹配结果.csv",
            mime="text/csv"
        )

        if unmatched:
            st.warning(f"⚠️ 有 {len(unmatched)} 个 SKU 未匹配成功，示例如下：")
            st.text("\n".join(unmatched[:10]))

    except Exception as e:
        st.error(f"❌ 出错啦：{e}")
