import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="NailVesta 入库匹配工具（支持 PDF 多表预览）", layout="wide")
st.title("💅 NailVesta 入库匹配工具（入库数量输出｜支持 PDF 多表预览）")

# ============== 上传文件区 ==============
stock_file = st.file_uploader("📦 上传库存表（必须包含『SKU编码』列，如 NPX014-S）", type=["csv", "xlsx"])
entry_file = st.file_uploader("📝 上传入库表（支持 CSV/XLSX/PDF）", type=["csv", "xlsx", "pdf"])

# ============== 工具函数 ==============
def read_stock(file):
    if file.name.endswith(".csv"):
        return pd.read_csv(file, encoding="utf-8-sig")
    else:
        return pd.read_excel(file)

def _normalize_header(s):
    if s is None: return ""
    s = str(s).strip().replace("\n","").replace(" ","")
    s = s.replace("（","(").replace("）",")")
    return s

def clean_base(s):
    s = str(s).strip()
    s = re.sub(r"\s+","", s)
    s = s.replace("（","(").replace("）",")")
    s = re.sub(r"(补寄|加单|重发|备注).*","", s)
    m = re.search(r"[A-Z]{2,4}\d{3}", s)
    return m.group(0) if m else s

# ============== PDF 解析（多表预览） ==============
def extract_tables_from_pdf(file_obj, page_from=1, page_to=9999, keyword=""):
    import pdfplumber
    tables = []
    with pdfplumber.open(file_obj) as pdf:
        total_pages = len(pdf.pages)
        p1, p2 = max(1, int(page_from)), min(total_pages, int(page_to))
        for i in range(p1-1, p2):
            page = pdf.pages[i]
            if keyword:
                head_text = (page.extract_text() or "")[:300]
                if keyword not in head_text:
                    continue
            page_tables = page.extract_tables() or []
            for tbl in page_tables:
                if tbl and len(tbl) > 1:
                    tables.append(tbl)
    return tables

def convert_table_to_df(tbl):
    header = [_normalize_header(x) for x in tbl[0]]
    width = len(header)
    rows = []
    for r in tbl[1:]:
        rr = list(r) + [""] * max(0, width - len(r))
        rows.append(rr[:width])
    df = pd.DataFrame(rows, columns=header)
    # 标准化列名
    df.columns = [c.lower() for c in df.columns]
    # 找列
    sku_col = next((c for c in df.columns if "sku" in c or "小盒子" in c or "下单编号" in c), None)
    s_col   = next((c for c in df.columns if c.startswith("s")), None)
    m_col   = next((c for c in df.columns if c.startswith("m")), None)
    l_col   = next((c for c in df.columns if c.startswith("l")), None)
    if not all([sku_col, s_col, m_col, l_col]):
        raise ValueError(f"该表格未找到完整列，现有列：{df.columns}")
    out = df[[sku_col, s_col, m_col, l_col]].copy()
    out.columns = ["SKU 编码", "S数量", "M数量", "L数量"]
    out["SKU 编码"] = out["SKU 编码"].apply(clean_base)
    for c in ["S数量","M数量","L数量"]:
        out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0).round().clip(lower=0).astype(int)
    return out

def build_entry_map(entry_df):
    entry_map = {}
    for _, row in entry_df.iterrows():
        base = str(row["SKU 编码"]).strip()
        for size, col in zip(["S","M","L"], ["S数量","M数量","L数量"]):
            qty = int(row[col])
            if qty > 0:
                full = f"{base}-{size}"
                entry_map[full] = entry_map.get(full, 0) + qty
    return entry_map

# ============== 主流程 ==============
if stock_file and entry_file:
    try:
        stock_df = read_stock(stock_file)
        if "SKU编码" not in stock_df.columns:
            st.error("❌ 库存表缺少『SKU编码』列")
            st.stop()
        stock_skus = stock_df["SKU编码"].dropna().astype(str).str.strip().tolist()

        if entry_file.name.lower().endswith(".pdf"):
            with st.sidebar:
                st.header("PDF 解析范围")
                page_from = st.number_input("起始页", min_value=1, value=1)
                page_to   = st.number_input("结束页", min_value=1, value=50)
                keyword   = st.text_input("标题关键词过滤（可选）", value="")

            tables = extract_tables_from_pdf(entry_file, page_from, page_to, keyword)
            if not tables:
                st.error("⚠️ 在选定范围内未识别到表格")
                st.stop()

            # 显示候选表格
            st.subheader("🔍 PDF 表格预览")
            options = [f"Table #{i+1}" for i in range(len(tables))]
            choice = st.selectbox("选择要使用的表格", options)
            idx = options.index(choice)
            entry_df_raw = convert_table_to_df(tables[idx])
            st.dataframe(entry_df_raw.head(20), use_container_width=True)

        else:
            entry_df_raw = read_stock(entry_file)

        # 构建映射
        entry_map = build_entry_map(entry_df_raw)

        # 匹配
        results, unmatched, total_in = [], [], 0
        for sku in stock_skus:
            qty = entry_map.get(sku, "")
            results.append((sku, qty))
            if qty == "":
                unmatched.append(sku)
            else:
                total_in += qty
        result_df = pd.DataFrame(results, columns=["SKU编码","入库数量"])

        st.success(f"✅ 匹配完成！匹配到 {result_df['入库数量'].replace('',0).astype(int).gt(0).sum()} 个 SKU，累计 {total_in} 件")
        st.dataframe(result_df, use_container_width=True)

        st.markdown("### 📋 可复制入库数量列（顺序对齐库存表）")
        st.code("\n".join([str(x) for x in result_df["入库数量"].tolist()]), language="text")

        st.download_button(
            "📥 下载入库数量 CSV",
            result_df.to_csv(index=False).encode("utf-8-sig"),
            "NailVesta_入库数量.csv",
            "text/csv"
        )
        if unmatched:
            st.warning("⚠️ 未匹配到的 SKU 示例：\n" + "\n".join(unmatched[:10]))

    except Exception as e:
        st.error(f"❌ 出错：{e}")
