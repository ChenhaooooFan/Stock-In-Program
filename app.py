import streamlit as st
import pandas as pd

st.set_page_config(page_title="NailVesta 入库程序", layout="wide")
st.title("💅 NailVesta 入库程序（纯 Excel 版）")

stock_file = st.file_uploader("📄 上传库存表（含 SKU，第3列）", type=["csv", "xlsx"])
entry_file = st.file_uploader("📄 上传入库表（含 SKU 第3列 + S/M/L 在第9/10/11列）", type=["csv", "xlsx"])

if stock_file and entry_file:
    try:
        # 自动识别文件格式
        if stock_file.name.endswith("csv"):
            stock_df = pd.read_csv(stock_file)
        else:
            stock_df = pd.read_excel(stock_file)

        if entry_file.name.endswith("csv"):
            entry_df = pd.read_csv(entry_file)
        else:
            entry_df = pd.read_excel(entry_file)

        # 获取库存 SKU 列（第3列）
        stock_skus = stock_df.iloc[:, 2].dropna().astype(str).tolist()

        # 构造入库 SKU 映射表（基于不带尺码的 SKU）
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

        # 匹配生成入库列
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

        st.success("✅ 已生成入库数量")
        st.dataframe(result_df, use_container_width=True)

        st.markdown("### 📋 可复制入库数量列：")
        st.code("\n".join([str(q) for q in output_quantities if str(q).strip() != ""]), language="text")

        st.download_button(
            label="📥 下载结果 CSV",
            data=result_df.to_csv(index=False).encode("utf-8-sig"),
            file_name="入库数量匹配结果.csv",
            mime="text/csv"
        )

        if unmatched_skus:
            st.warning(f"⚠️ 有 {len(unmatched_skus)} 个 SKU 未匹配成功，示例如下：")
            st.text("\n".join(unmatched_skus[:10]))

    except Exception as e:
        st.error(f"❌ 出错啦：{e}")
