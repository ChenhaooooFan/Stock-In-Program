import streamlit as st
import pandas as pd

st.set_page_config(page_title="NailVesta 入库程序", layout="wide")
st.title("💅 NailVesta 入库程序（纯 Excel/CSV 支持）")

# 上传文件
stock_file = st.file_uploader("📄 上传库存表（SKU 在第3列）", type=["csv", "xlsx"])
entry_file = st.file_uploader("📄 上传入库表（SKU 在第3列，S/M/L 在第9/10/11列）", type=["csv", "xlsx"])

# 文件读取函数
def read_file(file):
    if file.name.endswith("csv"):
        return pd.read_csv(file)
    else:
        return pd.read_excel(file)

if stock_file and entry_file:
    try:
        stock_df = read_file(stock_file)
        entry_df = read_file(entry_file)

        # 读取库存 SKU 列（第3列）
        stock_skus = stock_df.iloc[:, 2].dropna().astype(str).tolist()

        # 构建入库 SKU 映射（base SKU → S/M/L）
        entry_map = {}
        for _, row in entry_df.iterrows():
            try:
                base_sku = str(row.iloc[2])
                s = int(row.iloc[8])
                m = int(row.iloc[9])
                l = int(row.iloc[10])
                entry_map[f"{base_sku}-S"] = s
                entry_map[f"{base_sku}-M"] = m
                entry_map[f"{base_sku}-L"] = l
            except:
                continue

        # 生成匹配结果
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

        st.success("✅ 入库数量已生成")
        st.dataframe(result_df, use_container_width=True)

        st.download_button(
            label="📥 下载 CSV",
            data=result_df.to_csv(index=False).encode("utf-8-sig"),
            file_name="入库匹配结果.csv",
            mime="text/csv"
        )

        st.markdown("### 📋 可复制的入库数量列")
        st.code("\n".join([str(i) for i in output_quantities if str(i).strip() != ""]), language="text")

        if unmatched_skus:
            st.warning(f"⚠️ 有 {len(unmatched_skus)} 个 SKU 未匹配成功，示例：")
            st.text("\n".join(unmatched_skus[:10]))

    except Exception as e:
        st.error(f"❌ 出错啦：{e}")
