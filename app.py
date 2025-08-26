import streamlit as st
import pandas as pd
import re

# ============== 页面设置 ==============
st.set_page_config(page_title="NailVesta 入库匹配工具（支持 PDF）", layout="wide")
st.title("💅 NailVesta 入库匹配工具（仅输出入库数量｜支持 CSV/XLSX/PDF）")

# ============== 工具函数 ==============
@st.cache_data(show_spinner=False)
def read_any_table(file):
    """读取 CSV/XLSX 为 DataFrame；PDF 使用 pdfplumber 解析为 DataFrame（自动找表、清洗列）"""
    name = file.name.lower()
    if name.endswith(".csv"):
        # 兼容带 BOM
        try:
            return pd.read_csv(file, encoding="utf-8-sig")
        except Exception:
            file.seek(0)
            return pd.read_csv(file)
    elif name.endswith(".xlsx"):
        return pd.read_excel(file)
    elif name.endswith(".pdf"):
        # 延迟导入，避免非 PDF 也要求安装 pdfplumber
        import pdfplumber
        return read_pdf_to_df(file)
    else:
        raise ValueError("不支持的文件格式，请上传 CSV / XLSX / PDF")

def _normalize_header(s):
    if s is None: 
        return ""
    s = str(s).strip()
    s = s.replace("\n", "").replace(" ", "")
    s = s.replace("（", "(").replace("）", ")")
    return s

def read_pdf_to_df(file_obj) -> pd.DataFrame:
    """使用 pdfplumber 解析 PDF 表格，输出至少包含 SKU 编码、S数量、M数量、L数量 四列（若能识别）。"""
    import pdfplumber
    rows = []
    with pdfplumber.open(file_obj) as pdf:
        for page in pdf.pages:
            page_tables = page.extract_tables() or []
            for tbl in page_tables:
                if not tbl or len(tbl) < 2:
                    continue
                header = [_normalize_header(x) for x in tbl[0]]
                width = len(header)
                if width < 2:
                    continue
                for r in tbl[1:]:
                    rr = list(r) + [""] * max(0, width - len(r))
                    rr = rr[:width]
                    rows.append(dict(zip(header, rr)))
    if not rows:
        raise ValueError("未在 PDF 中识别到可用表格，请确认 PDF 为可复制表格（非纯图片）。")

    df = pd.DataFrame(rows)

    # 标准化列名
    norm_map = {c: _normalize_header(c).lower() for c in df.columns}
    df.columns = [norm_map[c] for c in df.columns]

    # 自动识别 4 列
    sku_col, s_col, m_col, l_col = auto_pick_entry_columns(df)
    if not all([sku_col, s_col, m_col, l_col]):
        raise ValueError(f"PDF 解析完成，但未找到完整列：'SKU 编码'、'S数量'、'M数量'、'L数量'。当前列：{list(df.columns)[:12]}...")

    out = df[[sku_col, s_col, m_col, l_col]].copy()
    out.columns = ["SKU 编码", "S数量", "M数量", "L数量"]

    # 清洗 SKU 基码（例如去掉备注“补寄M”等，只保留形如 NPX014）
    def clean_base(s):
        s = str(s).strip()
        s = re.sub(r"\s+", "", s)
        s = s.replace("（", "(").replace("）", ")")
        s = re.sub(r"(补寄|加单|重发|备注).*", "", s)
        m = re.search(r"[A-Z]{2,4}\d{3}", s)
        return m.group(0) if m else s

    out["SKU 编码"] = out["SKU 编码"].apply(clean_base)

    for c in ["S数量", "M数量", "L数量"]:
        out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0).round().clip(lower=0).astype(int)

    return out

def auto_pick_entry_columns(df: pd.DataFrame):
    """从 DataFrame（列名已标准化为小写、去空格）自动挑选：SKU/S/M/L 列"""
    cols = list(df.columns)

    def pick_first(keys):
        for k in keys:
            if k in cols:
                return k
        # 模糊包含
        for c in cols:
            for k in keys:
                if k in c:
                    return c
        return None

    # 可能的列名（已标准化）
    sku_keys = ["sku编码", "sku", "skucode", "sku编号", "sku編碼", "sku编码(必填)", "sku编码（必填）", "小盒子", "下单编号"]
    s_keys   = ["s数量", "sqty", "s件数", "s码数量", "s"]
    m_keys   = ["m数量", "mqty", "m件数", "m码数量", "m"]
    l_keys   = ["l数量", "lqty", "l件数", "l码数量", "l"]

    sku_col = pick_first(sku_keys)
    s_col   = pick_first(s_keys)
    m_col   = pick_first(m_keys)
    l_col   = pick_first(l_keys)
    return sku_col, s_col, m_col, l_col

def build_entry_map(entry_df: pd.DataFrame, sku_col="SKU 编码", s_col="S数量", m_col="M数量", l_col="L数量"):
    """构建 full_sku -> 数量 的映射（累计同一 SKU 多行）"""
    # 列名容错：尝试标准化为目标命名
    cols_norm = {c: _normalize_header(c) for c in entry_df.columns}
    inv = {v: k for k, v in cols_norm.items()}
    sku_col = inv.get(_normalize_header(sku_col), sku_col)
    s_col   = inv.get(_normalize_header(s_col),   s_col)
    m_col   = inv.get(_normalize_header(m_col),   m_col)
    l_col   = inv.get(_normalize_header(l_col),   l_col)

    # 若列名不匹配，再自动挑选一次
    needed = [sku_col, s_col, m_col, l_col]
    if any(col not in entry_df.columns for col in needed):
        # 将列名标准化后再自动挑选
        df2 = entry_df.copy()
        df2.columns = [ _normalize_header(c).lower() for c in df2.columns ]
        sku_pick, s_pick, m_pick, l_pick = auto_pick_entry_columns(df2)
        if not all([sku_pick, s_pick, m_pick, l_pick]):
            raise ValueError(f"入库表缺少必要列：{needed}，且自动识别失败。当前列：{list(entry_df.columns)[:12]}...")
        entry_df = df2[[sku_pick, s_pick, m_pick, l_pick]].copy()
        entry_df.columns = ["SKU 编码", "S数量", "M数量", "L数量"]
        sku_col, s_col, m_col, l_col = "SKU 编码", "S数量", "M数量", "L数量"

    # 规范化数量
    for c in [s_col, m_col, l_col]:
        entry_df[c] = pd.to_numeric(entry_df[c], errors="coerce").fillna(0).round().clip(lower=0).astype(int)

    # 清洗 SKU 基码
    def clean_base(s):
        s = str(s).strip()
        s = re.sub(r"\s+", "", s)
        s = s.replace("（", "(").replace("）", ")")
        s = re.sub(r"(补寄|加单|重发|备注).*", "", s)
        m = re.search(r"[A-Z]{2,4}\d{3}", s)
        return m.group(0) if m else s

    entry_df[sku_col] = entry_df[sku_col].apply(clean_base)

    entry_map = {}
    for _, row in entry_df.iterrows():
        base = str(row[sku_col]).strip()
        for size, col in zip(["S", "M", "L"], [s_col, m_col, l_col]):
            qty = int(row[col])
            if qty > 0:
                full = f"{base}-{size}"
                entry_map[full] = entry_map.get(full, 0) + qty
    return entry_map, entry_df

# ============== 上传文件区 ==============
stock_file = st.file_uploader("📦 上传库存表（必须包含『SKU编码』列，如 NPX014-S）", type=["csv", "xlsx"])
entry_file = st.file_uploader("📝 上传入库表（支持 CSV / XLSX / PDF，需含『SKU 编码』『S数量』『M数量』『L数量』）", type=["csv", "xlsx", "pdf"])

# ============== 主流程 ==============
if stock_file and entry_file:
    try:
        stock_df = read_any_table(stock_file)
        entry_df_raw = read_any_table(entry_file)

        # 库存表校验
        if "SKU编码" not in stock_df.columns:
            st.error("❌ 库存表缺少『SKU编码』列。请确保表头为“SKU编码”（示例：NPX014-S）。")
            st.stop()

        stock_skus = (
            stock_df["SKU编码"].dropna().astype(str).str.strip().tolist()
        )
        if len(stock_skus) == 0:
            st.error("❌ 库存表『SKU编码』为空。")
            st.stop()

        st.subheader("🧾 入库表预览（前 20 行）")
        st.dataframe(entry_df_raw.head(20), use_container_width=True)

        # 构建入库映射（自动识别列名，累计同 SKU）
        entry_map, entry_df_clean = build_entry_map(entry_df_raw)

        # 生成匹配结果，与库存表顺序逐行对齐
        results, unmatched, total_in = [], [], 0
        for sku in stock_skus:
            qty = entry_map.get(sku, "")
            results.append((sku, qty))
            if qty == "":
                unmatched.append(sku)
            else:
                total_in += qty

        result_df = pd.DataFrame(results, columns=["SKU编码", "入库数量"])

        st.success(f"✅ 匹配完成！匹配到 {result_df['入库数量'].replace('', 0).astype(int).gt(0).sum()} 个 SKU，累计 {total_in} 件。")
        st.dataframe(result_df, use_container_width=True)

        st.markdown("### 📋 可复制入库数量列（与库存表顺序一一对应）")
        copy_col = "\n".join([str(x) for x in result_df["入库数量"].tolist()])
        st.code(copy_col, language="text")

        st.download_button(
            "📥 下载入库数量 CSV",
            result_df.to_csv(index=False).encode("utf-8-sig"),
            "NailVesta_入库数量.csv",
            "text/csv"
        )

        # 诊断信息
        if unmatched:
            st.warning("⚠️ 未匹配到入库数量的库存 SKU（前 10 条）：\n" + "\n".join(unmatched[:10]))

        with st.expander("🔎 调试信息（解析后的入库表前 20 行 & 列名）"):
            st.write("入库表列名：", list(entry_df_clean.columns))
            st.dataframe(entry_df_clean.head(20), use_container_width=True)

    except Exception as e:
        st.error(f"❌ 出错：{e}")

else:
    st.info("👆 请先上传『库存表』与『入库表』（CSV/XLSX/PDF）。")
