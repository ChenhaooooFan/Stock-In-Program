
import streamlit as st
import pandas as pd
import numpy as np

st.title("NailVesta 入库程序")

# 上传文件
inventory_file = st.file_uploader("上传 NailVesta 产品库存表", type=["csv"])
entry_file = st.file_uploader("上传入库表（含 SKU 和 S/M/L 数量）", type=["csv", "xlsx"])

if inventory_file and entry_file:
    # 读取库存文件
    inventory_df = pd.read_csv(inventory_file)
    inventory_df = inventory_df.dropna(subset=['SKU编码'])

    # 读取入库文件
    try:
        if entry_file.name.endswith(".csv"):
            entry_df = pd.read_csv(entry_file)
        else:
            entry_df = pd.read_excel(entry_file)
    except Exception as e:
        st.error(f"读取入库表时出错: {e}")

    # 提取 SKU 和数量（不带尺码的）
    raw_skus = entry_df.iloc[:, 3]  # 第4列是 SKU，不含尺码
    qty_S = entry_df.iloc[:, 8]    # 第9列是 S
    qty_M = entry_df.iloc[:, 9]    # 第10列是 M
    qty_L = entry_df.iloc[:, 10]   # 第11列是 L

    # 构造 SKU+尺码 对应数量
    incoming_dict = {}
    for sku, s, m, l in zip(raw_skus, qty_S, qty_M, qty_L):
        if pd.notna(sku):
            incoming_dict[f"{sku}-S"] = int(s) if not pd.isna(s) else 0
            incoming_dict[f"{sku}-M"] = int(m) if not pd.isna(m) else 0
            incoming_dict[f"{sku}-L"] = int(l) if not pd.isna(l) else 0

    # 匹配入库数量
    matched_qty = []
    for sku in inventory_df['SKU编码']:
        matched_qty.append(incoming_dict.get(sku, 0))

    # 显示并复制结果
    st.success("以下是匹配的入库数量，可直接复制粘贴")
    result_series = pd.Series(matched_qty)
    result_str = "\n".join(result_series.astype(str).tolist())
    st.text_area("入库数量列表", result_str, height=400)

    st.download_button("下载为 CSV", result_series.to_csv(index=False), file_name="入库数量.csv")
