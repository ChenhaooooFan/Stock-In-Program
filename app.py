import streamlit as st
import pandas as pd

st.set_page_config(page_title="NailVesta 入库程序", layout="wide")
st.title("💅 NailVesta 入库程序（基于 SKU编码 列精准匹配）")

# 上传文件
stock_file = st.file_uploader("📦 上传库存表（SKU 编码列名为 SKU编码）", type=["csv", "xlsx"])
entry_file = st.file_uploader("📝 上传入库表（SKU 编码在第4列，S/M/L 在第9/10/11列）", type=["csv", "xlsx"])

# 读取函数
def read_file(file):
    if file.name.endswith("csv"):
        return pd.read_csv(file)
    else:
        return pd.read_excel(file)

if stock_file and entry_file:
    try:
        stock_df = read_file(stock_file)
        entry_df = read_file(entry_file)

        # 提取库存中的完整 SKU（SKU编码列）
        if "SKU编码" not in stock_df.columns:
            st.error("❌ 库存表中未找到列名为 'SKU编码' 的列")
            st.stop()

        stock_skus = stock_df["SKU编码"].dropna().astype(str).str.strip().tolist()

        # 构建 SKU → 入库数量 映射
        entry_map = {}
        for _, row in entry_df.iterrows():
            try:
                sku = str(row.iloc[3]).strip()
                s = int(row.iloc[8])
                m = int(row.iloc[9])
                l = int(row.iloc[10])
                entry_map[f"{sku}-S"] = s
                entry_map[f"{sku}-M"] = m
                entry_map[f"{sku}-L"] = l
            except:
                continue

        # 对照库存表生成最终列表
        final_skus = []
        final_qtys = []
        unmatched = []

        for sku in stock_skus:
            final_skus.append(sku)
            if sku in entry_map:
                final_qtys.append(entry_map[sku])
            else:
                final_qtys.append("")
                unmatched.append(sku)

        result_df = pd.DataFrame({
            "SKU": final_skus,
            "入库数量": final_qtys
        })

        st.success("✅ 入库匹配成功！")
        st.dataframe(result_df, use_container_width=True)

        st.markdown("### 📋 可复制入库数量列")
        st.code("\n".join([str(q) for q in final_qtys if str(q).strip() != ""]), language="text")

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
