import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# 設定網頁標題與寬度
st.set_page_config(page_title="全球港口績效動態儀表板", layout="wide")

# ==============================================================================
# 🎯 終極智慧清洗：用關鍵字「盲抓」真正需要的欄位
# ==============================================================================
@st.cache_data
def load_and_clean_data():
    file_name = "US_PortCalls_S.csv"
    try:
        # 自動忽略可能導致解析錯誤的爛行
        df = pd.read_csv(file_name, on_bad_lines='skip')
    except Exception as e:
        st.error(f"❌ 無法讀取 CSV 檔案：{e}")
        return pd.DataFrame()

    # 清除欄位前後的隱形空格，全部轉小寫方便比對
    df.columns = df.columns.str.strip()
    col_raw = df.columns.tolist()
    col_low = [c.lower() for c in col_raw]
    
    new_df = pd.DataFrame()

    # 1. 尋找「經濟體/國家文字描述」欄位
    # 優先找同時包含 economy 和 label 的，或是包含 country, name, label 的文字欄
    eco_col = None
    for i, cl in enumerate(col_low):
        if "economy" in cl and "label" in cl:
            eco_col = col_raw[i]
            break
    if not eco_col:
        for i, cl in enumerate(col_low):
            if "label" in cl or "country" in cl or "economy" in cl:
                # 排除純數字的 code 欄位
                if "code" not in cl:
                    eco_col = col_raw[i]
                    break
    # 真的找不到就用第一欄
    new_df['economy_label'] = df[eco_col] if eco_col else df.iloc[:, 0]

    # 2. 尋找「船舶類型描述」欄位
    vess_col = None
    for i, cl in enumerate(col_low):
        if "vessel" in cl and "label" in cl:
            vess_col = col_raw[i]
            break
    if not vess_col:
        for i, cl in enumerate(col_low):
            if "vessel" in cl or "ship" in cl:
                if "code" not in cl:
                    vess_col = col_raw[i]
                    break
    new_df['vessel_type'] = df[vess_col] if vess_col else df.iloc[:, 1]

    # 3. 尋找「時間期間」欄位
    per_col = None
    for i, cl in enumerate(col_low):
        if "period" in cl or "year" in cl or "date" in cl:
            per_col = col_raw[i]
            break
    new_df['period'] = df[per_col] if per_col else (df.iloc[:, 8] if df.shape[1] >= 9 else df.iloc[:, -1])

    # 4. 尋找「在港停泊時間 (數值)」欄位
    time_col = None
    for i, cl in enumerate(col_low):
        if "time" in cl or "spent" in cl or "days" in cl:
            if "value" in cl or "median" in cl or "avg" in cl or "average" in cl:
                time_col = col_raw[i]
                break
    if not time_col:
        for i, cl in enumerate(col_low):
            if "time" in cl or "port" in cl:
                time_col = col_raw[i]
                break
    
    # 5. 尋找「船舶大小/噸位 (數值)」欄位
    size_col = None
    for i, cl in enumerate(col_low):
        if "size" in cl or "gt" in cl or "tonnage" in cl:
            size_col = col_raw[i]
            break

    # 數值轉換與雙引號拔除
    def clean_to_numeric(series):
        s = series.astype(str).str.replace('"', '').str.replace("'", "").str.strip()
        s = s.replace(["Not available or not separately reported", "nan", "NaN", "null", ""], np.nan)
        return pd.to_numeric(s, errors='coerce')

    new_df['median_time_in_port'] = clean_to_numeric(df[time_col]) if time_col else clean_to_numeric(df.iloc[:, 3])
    new_df['avg_size_GT'] = clean_to_numeric(df[size_col]) if size_col else clean_to_numeric(df.iloc[:, 4])

    # 基礎文字清洗
    new_df['economy_label'] = new_df['economy_label'].astype(str).str.replace('"', '').str.strip()
    new_df['vessel_type'] = new_df['vessel_type'].astype(str).str.replace('"', '').str.strip()
    new_df['period'] = new_df['period'].astype(str).str.replace('"', '').str.strip()

    # 剔除表格內的雜訊行（例如把欄位名稱重複當成資料列的狀況）
    mask = (
        (~new_df['period'].str.contains('Period|Label', case=False, na=False)) & 
        (~new_df['economy_label'].str.contains('Economy|Country|Code', case=False, na=False)) &
        (new_df['median_time_in_port'].notna()) # 確保時間有值，不抓垃圾空行
    )
    new_df = new_df[mask].reset_index(drop=True)
    
    return new_df

df_cleaned = load_and_clean_data()

# ==============================================================================
# 🎛️ 前端網頁渲染
# ==============================================================================
if df_cleaned.empty:
    st.error("⚠️ 無法成功解析任何有效的海事數據，請展開下方檢查原始欄位名稱。")
    # 顯示欄位偵測幫助除錯
    try:
        raw_df = pd.read_csv("US_PortCalls_S.csv", nrows=5)
        st.write("原始 CSV 欄位名稱如下，請檢查是否對應：", raw_df.columns.tolist())
        st.dataframe(raw_df)
    except:
        pass
else:
    st.sidebar.header("📊 數據篩選中心")

    # 1. 期間篩選器
    all_periods = sorted([x for x in df_cleaned['period'].unique() if x not in ["nan", "Unknown", ""]])
    if all_periods:
        selected_period = st.sidebar.selectbox("選擇報告期間 (Period)", all_periods, index=len(all_periods)-1)
        filtered_df = df_cleaned[df_cleaned['period'] == selected_period]
    else:
        selected_period = "所有期間"
        filtered_df = df_cleaned.copy()

    # 2. 船舶類型篩選器
    all_vessels = sorted([x for x in filtered_df['vessel_type'].unique() if x not in ["nan", ""]])
    if all_vessels:
        # 儘量勾選多一點，免得漏看
        default_vessels = [v for v in all_vessels if "all" in v.lower() or "container" in v.lower()]
        if not default_vessels:
            default_vessels = all_vessels
        selected_vessels = st.sidebar.multiselect("選擇船舶類型", all_vessels, default=default_vessels)
        filtered_df = filtered_df[filtered_df['vessel_type'].isin(selected_vessels)]
    else:
        st.sidebar.warning("當前期間無可用船型描述")

    # 3. 顯示國家數量
    max_countries = st.sidebar.slider("畫面上顯示前幾名效率排行國家", min_value=5, max_value=40, value=15)

    # --- 主網頁畫面 ---
    st.title("⚓️ 全球海事港口績效動態儀表板")
    st.markdown(f"**當前分析期間： `{selected_period}`** | 智慧關鍵字搜尋技術已啟動。")
    st.write("---")

    # 💡 第一層：折線圖
    st.header("📈 各經濟體港口停泊時間對比")
    
    plot_df = filtered_df.sort_values(by='median_time_in_port', ascending=False).head(max_countries)
    
    if not plot_df.empty:
        fig_line = px.line(
            plot_df,
            x='economy_label',
            y='median_time_in_port',
            color='vessel_type',
            title=f"各經濟體船舶在港中位數時間排行 (前 {max_countries} 名)",
            labels={'economy_label': '經濟體/國家', 'median_time_in_port': '停泊中位數時間 (天)', 'vessel_type': '船舶類型'},
            markers=True,
            template="ggplot2"
        )
        fig_line.update_layout(xaxis_tickangle=-45, height=600)
        st.plotly_chart(fig_line, use_container_width=True)
    else:
        st.warning("⚠️ 此篩選條件下沒有對應數據。")

    st.write("---")

    # 💡 第二層：雙變量統計箱線圖
    st.header("📊 進階統計：船舶類型 vs 港口核心指標分佈 (Boxplot)")

    tab1, tab2 = st.tabs(["⏳ 在港停泊時間分佈", "🚢 船舶平均總噸位(GT)分佈"])

    with tab1:
        if not filtered_df.empty:
            fig_box1 = px.box(
                filtered_df,
                x='vessel_type',
                y='median_time_in_port',
                color='vessel_type',
                title="不同船舶類型的港口停泊時間統計分佈",
                labels={'vessel_type': '船舶類型', 'median_time_in_port': '在港時間 (天)'},
                points="all",
                template="ggplot2"
            )
            fig_box1.update_layout(height=500, showlegend=False, xaxis_tickangle=-25)
            st.plotly_chart(fig_box1, use_container_width=True)

    with tab2:
        if not filtered_df.empty:
            fig_box2 = px.box(
                filtered_df,
                x='vessel_type',
                y='avg_size_GT',
                color='vessel_type',
                title="不同船舶類型的平均總噸位 (GT) 統計分佈",
                labels={'vessel_type': '船舶類型', 'avg_size_GT': '平均總噸位 (GT)'},
                points="all",
                template="ggplot2"
            )
            fig_box2.update_layout(height=500, showlegend=False, xaxis_tickangle=-25)
            st.plotly_chart(fig_box2, use_container_width=True)

    # 底部數據檢查器
    with st.expander("🔍 檢視當前動態資料集摘要"):
        st.dataframe(filtered_df)
