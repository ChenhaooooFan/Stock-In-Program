import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="NailVesta 入库程序", layout="wide")
st.title("💅 NailVesta 入库程序（基于 SKU 编码）")

# 文件上传
stock_file = st.file_uploader("📦 上传库存表（SKU 编码在 D 列，第 4 列）", type=["csv", "xlsx"])
entry_file = st.file_uploader("📝 上传入库表（SKU 编码在 D 列，第 4 列，S/M/L 在第 9/10/11 列）", type=["csv", "xlsx"])

# 读取函数
def read_file(file):
    if file.name.endswith("csv"):
        return pd.read_csv(file)
    else:
        return pd.read_excel(file)

# SKU 编码检测（如 NPJ005）
def is_valid_sku(s):
    return isinstance(s, str) and re.match(r"^[A-Z]{2,3}[A-Z]?\d{3}$", s)

if stock_file and entry_file:
    try:
        stock_df = read_file(stock_file)
        entry_df = read_file(entry_file)

        # 提取库存表 D 列中有效 SKU（索引为 3）
        stock_skus_raw = stock_df.iloc[:, 3].dropna().astype(str)
        stock_skus = [sku for sku in stock_skus_raw if is_valid_sku(sku)]

        # 构建入库 SKU+尺码 → 数量 映射
        entry_map = {}
        for _, row in entry_df.iterrows():
            try:
                base_sku = str(row.iloc[3]).strip()  # 第4列：编码
                s = int(row.iloc[8])  # 第9列
                m = int(row.iloc[9])  # 第10列
                l = int(row.iloc[10]) # 第11列
                entry_map[f"{base_sku}-S"] = s
                entry_map[f"{base_sku}-M"] = m
                entry_map[f"{base_sku}-L"] = l
            except:
                continue

        # 生成 SKU+尺码顺序列表
        expanded_skus = []
        for sku in stock_skus:
            expanded_skus.extend([f"{sku}-S", f"{sku}-M", f"{sku}-L"])

        # 对照生成入库数量列
        output_qtys = []
        unmatched = []
        for sku in expanded_skus:
            if sku in entry_map:
                output_qtys.append(entry_map[sku])
            else:
                output_qtys.append("")
                unmatched.append(sku)

        result_df = pd.DataFrame({
            "SKU": expanded_skus,
            "入库数量": output_qtys
        })

        st.success("✅ 入库匹配成功！")
        st.dataframe(result_df, use_container_width=True)

        st.markdown("### 📋 可复制入库数量列")
        st.code("\n".join([str(q) for q in output_qtys if str(q).strip() != ""]), language="text")

        st.download_button(
            label="📥 下载结果 CSV",
            data=result_df.to_csv(index=False).encode("utf-8-sig"),
            file_name="NailVesta_入库匹配结果.csv",
            mime="text/csv"
        )

        if unmatched:
            st.warning(f"⚠️ 共 {len(unmatched)} 个 SKU 未匹配成功，示例：")
            st.text("\n".join(unmatched[:10]))

    except Exception as e:
        st.error(f"❌ 出错了：{e}")
