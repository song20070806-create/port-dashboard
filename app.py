import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# 設定網頁標題與寬度
st.set_page_config(page_title="全球港口績效動態儀表板", layout="wide")

@st.cache_data
def load_and_clean_data():
    file_name = "US_PortCalls_S.csv"
    try:
        df = pd.read_csv(file_name)
    except Exception as e:
        st.error(f"❌ 無法讀取 CSV 檔案：{e}")
        return pd.DataFrame()

    # 確保拔除欄位名稱前後的隱形空格
    df.columns = df.columns.str.strip()
    
    new_df = pd.DataFrame()
    
    # 精準對應官方欄位
    new_df['economy_label'] = df['Economy_Label'].astype(str).str.strip()
    new_df['vessel_type'] = df['CommercialMarket_Label'].astype(str).str.strip()
    new_df['period'] = df['period'].astype(str).str.strip()

    # 安全轉換數值函數
    def to_numeric_clean(series):
        s = series.astype(str).str.replace('"', '').str.strip()
        s = s.replace(["Not available or not separately reported", "nan", "NaN", "null", ""], np.nan)
        return pd.to_numeric(s, errors='coerce')

    # 讀取數值欄位
    if 'Median_time_in_port_days_Value' in df.columns:
        new_df['median_time_in_port'] = to_numeric_clean(df['Median_time_in_port_days_Value'])
    else:
        time_cols = [c for c in df.columns if "time_in_port" in c.lower()]
        new_df['median_time_in_port'] = to_numeric_clean(df[time_cols[0]]) if time_cols else to_numeric_clean(df.iloc[:, 5])

    if 'Average_size_GT_Value' in df.columns:
        new_df['avg_size_GT'] = to_numeric_clean(df['Average_size_GT_Value'])
    else:
        size_cols = [c for c in df.columns if "size_gt" in c.lower()]
        new_df['avg_size_GT'] = to_numeric_clean(df[size_cols[0]]) if size_cols else to_numeric_clean(df.iloc[:, 7])

    # 資料清洗：移除重複的標題列與 World 總計
    new_df = new_df[~new_df['period'].str.contains('period', case=False, na=False)]
    new_df = new_df[~new_df['economy_label'].str.contains('Economy|World', case=False, na=False)]
    
    # 剔除時間或船型為空值的行
    new_df = new_df.dropna(subset=['median_time_in_port']).reset_index(drop=True)
    
    return new_df

df_cleaned = load_and_clean_data()

# ==============================================================================
# 🎛️ 前端網頁渲染
# ==============================================================================
if df_cleaned.empty:
    st.error("⚠️ 資料集清洗後為空，請檢查 CSV 檔案欄位。")
else:
    st.sidebar.header("📊 數據篩選中心")

    # 1. 期間篩選器
    all_periods = sorted(list(df_cleaned['period'].unique()))
    selected_period = st.sidebar.selectbox("選擇報告期間 (Period)", all_periods, index=0)

    # 先切出該期間的資料
    period_df = df_cleaned[df_cleaned['period'] == selected_period]

    # 2. 船舶類型篩選器
    all_vessels = sorted(list(period_df['vessel_type'].unique()))
    
    # 🔥 修正點：預設直接勾選「全部可用船型」，避免因為漏勾導致畫面空白
    selected_vessels = st.sidebar.multiselect("選擇船舶類型", all_vessels, default=all_vessels)

    # 3. 限制顯示國家數
    max_countries = st.sidebar.slider("顯示國家數量", min_value=5, max_value=40, value=15)

    # 最終過濾資料
    filtered_df = period_df[period_df['vessel_type'].isin(selected_vessels)]

    # --- 主網頁畫面 ---
    st.title("⚓️ 全球海事港口績效動態儀表板")
    st.markdown(f"**當前分析期間： `{selected_period}`**")
    st.write("---")

    # 💡 第一層：分組長條圖
    st.header("📊 各經濟體港口停泊時間對比")
    
    if not filtered_df.empty:
        plot_df = filtered_df.sort_values(by='median_time_in_port', ascending=False).head(max_countries)
        fig_bar = px.bar(
            plot_df,
            x='economy_label',
            y='median_time_in_port',
            color='vessel_type',
            barmode='group',
            title=f"各經濟體船舶在港中位數時間排行 (期間: {selected_period})",
            labels={'economy_label': '經濟體/國家', 'median_time_in_port': '停泊中位數時間 (天)', 'vessel_type': '船舶類型'},
            template="plotly_dark",
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig_bar.update_layout(xaxis_tickangle=-45, height=550)
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        # 🔥 除錯機制：如果還是空的，直接把原因印在畫面上給我們看
        st.error(f"❌ 警告：在 `{selected_period}` 期間內找不到選定船型的資料！")
        st.write("請檢查下方目前該期間內實際存在的資料型態：")
        st.write(period_df.head(10))

    st.write("---")

    # 💡 第二層：統計箱線圖 (Boxplot)
    st.header("📊 進階統計：船舶類型與核心指標分佈 (Boxplot)")
    
    if not filtered_df.empty:
        tab1, tab2 = st.tabs(["⏳ 在港停泊時間分佈", "🚢 船舶平均總噸位 (GT) 分佈"])

        with tab1:
            fig_box1 = px.box(
                filtered_df,
                x='vessel_type',
                y='median_time_in_port',
                color='vessel_type',
                title="不同船舶類型的港口停泊時間分佈情況",
                labels={'vessel_type': '船舶類型', 'median_time_in_port': '在港時間 (天)'},
                points="all",
                template="plotly_dark"
            )
            fig_box1.update_layout(height=500, showlegend=False)
            st.plotly_chart(fig_box1, use_container_width=True)

        with tab2:
            fig_box2 = px.box(
                filtered_df,
                x='vessel_type',
                y='avg_size_GT',
                color='vessel_type',
                title="不同船舶類型的平均總噸位 (GT) 分佈情況",
                labels={'vessel_type': '船舶類型', 'avg_size_GT': '平均總噸位 (GT)'},
                points="all",
                template="plotly_dark"
            )
            fig_box2.update_layout(height=500, showlegend=False)
            st.plotly_chart(fig_box2, use_container_width=True)

    # 底部數據摘要檢查
    with st.expander("🔍 查看目前篩選的原始資料摘要"):
        st.dataframe(filtered_df)
