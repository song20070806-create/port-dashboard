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
        # 讀取 CSV
        df = pd.read_csv(file_name)
    except Exception as e:
        st.error(f"❌ 無法讀取 CSV 檔案：{e}")
        return pd.DataFrame()

    # 1. 確保拔除欄位名稱前後可能有的隱形空格
    df.columns = df.columns.str.strip()
    
    new_df = pd.DataFrame()
    
    # 2. 根據截圖精準對應欄位名稱
    # 國家/經濟體文字
    new_df['economy_label'] = df['Economy_Label'].astype(str).str.replace('"', '').str.strip()
    
    # 船舶類型文字（徹底修正！不再是數字了！）
    new_df['vessel_type'] = df['CommercialMarket_Label'].astype(str).str.replace('"', '').str.strip()
    
    # 時間報告期間
    new_df['period'] = df['period'].astype(str).str.replace('"', '').str.strip()

    # 3. 尋找並清洗數值欄位 (在港時間中位數、平均總噸位)
    # 由於名稱很長，我們用關鍵字精準從現有欄位抓取
    time_col = [c for c in df.columns if "Median_time_in_port" in c and "Value" in c]
    size_col = [c for c in df.columns if "Average_size_GT" in c and "Value" in c]
    
    def to_numeric_clean(series):
        s = series.astype(str).str.replace('"', '').str.strip()
        s = s.replace(["Not available or not separately reported", "nan", "NaN", "null", ""], np.nan)
        return pd.to_numeric(s, errors='coerce')

    if time_col:
        new_df['median_time_in_port'] = to_numeric_clean(df[time_col[0]])
    else:
        # 備用保底機制
        st.sidebar.warning("未偵測到精準時間欄位，啟用位置備用抓取")
        new_df['median_time_in_port'] = to_numeric_clean(df.iloc[:, 5])

    if size_col:
        new_df['avg_size_GT'] = to_numeric_clean(df[size_col[0]])
    else:
        new_df['avg_size_GT'] = to_numeric_clean(df.iloc[:, 7])

    # 4. 資料過濾：剔除雜訊與無效空值
    new_df = new_df[~new_df['period'].str.contains('period', case=False, na=False)]
    new_df = new_df[~new_df['economy_label'].str.contains('Economy', case=False, na=False)]
    
    # 排除世界總計(World)，我們只要看個別國家對比
    new_df = new_df[new_df['economy_label'].lower() != 'world']
    
    # 剔除沒有核心數值的行
    new_df = new_df.dropna(subset=['median_time_in_port']).reset_index(drop=True)
    
    return new_df

df_cleaned = load_and_clean_data()

# ==============================================================================
# 🎛️ 前端網頁渲染
# ==============================================================================
if df_cleaned.empty:
    st.error("⚠️ 資料集清洗後為空，請檢查 CSV 欄位命名是否與程式碼吻合。")
else:
    st.sidebar.header("📊 數據篩選中心")

    # 1. 期間篩選（確保不重複且排序）
    all_periods = sorted(list(df_cleaned['period'].unique()))
    selected_period = st.sidebar.selectbox("選擇報告期間 (Period)", all_periods, index=len(all_periods)-1 if all_periods else 0)

    # 先根據期間過濾，再抓取該期間存在的船舶類型
    period_df = df_cleaned[df_cleaned['period'] == selected_period]

    # 2. 船舶類型（真正的文字名稱，如 Container ships ！）
    all_vessels = sorted(list(period_df['vessel_type'].unique()))
    
    # 預設幫忙勾選常見的船型
    default_vessels = [v for v in all_vessels if "container" in v.lower() or "all ships" in v.lower()]
    if not default_vessels:
        default_vessels = all_vessels[:2] if all_vessels else []
        
    selected_vessels = st.sidebar.multiselect("選擇船舶類型", all_vessels, default=default_vessels)

    # 3. 限制顯示國家數
    max_countries = st.sidebar.slider("顯示國家數量", min_value=5, max_value=30, value=15)

    # 最終動態過濾
    filtered_df = period_df[period_df['vessel_type'].isin(selected_vessels)]

    st.title("⚓️ 全球海事港口績效動態儀表板")
    st.markdown(f"**當前分析期間： `{selected_period}`** | 欄位已由資料集成功結構化對應。")
    st.write("---")

    # 💡 主圖表：分組長條圖
    st.header("📊 各經濟體港口停泊時間對比")
    
    plot_df = filtered_df.sort_values(by='median_time_in_port', ascending=False).head(max_countries)
    
    if not plot_df.empty:
        fig_bar = px.bar(
            plot_df,
            x='economy_label',
            y='median_time_in_port',
            color='vessel_type',
            barmode='group',
            title=f"各經濟體船舶在港中位數時間排行 (前 {max_countries} 名)",
            labels={'economy_label': '經濟體/國家', 'median_time_in_port': '停泊中位數時間 (天)', 'vessel_type': '船舶類型'},
            template="plotly_dark"
        )
        fig_bar.update_layout(xaxis_tickangle=-45, height=550)
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.warning("⚠️ 當前篩選條件下無資料，請在左側勾選「船舶類型」。")

    st.write("---")

    # 💡 第二層：統計箱線圖 (Boxplot)
    st.header("📊 進階統計：船舶類型與核心指標分佈")
    
    tab1, tab2 = st.tabs(["⏳ 在港停泊時間分佈", "🚢 船舶平均總噸位(GT)分佈"])

    with tab1:
        if not filtered_df.empty:
            fig_box1 = px.box(
                filtered_df,
                x='vessel_type',
                y='median_time_in_port',
                color='vessel_type',
                title="不同船舶類型的港口停泊時間分佈",
                labels={'vessel_type': '船舶類型', 'median_time_in_port': '在港時間 (天)'},
                points="all",
                template="plotly_dark"
            )
            fig_box1.update_layout(height=500, showlegend=False, xaxis_tickangle=-15)
            st.plotly_chart(fig_box1, use_container_width=True)

    with tab2:
        if not filtered_df.empty:
            fig_box2 = px.box(
                filtered_df,
                x='vessel_type',
                y='avg_size_GT',
                color='vessel_type',
                title="不同船舶類型的平均總噸位 (GT) 分佈",
                labels={'vessel_type': '船舶類型', 'avg_size_GT': '平均總噸位 (GT)'},
                points="all",
                template="plotly_dark"
            )
            fig_box2.update_layout(height=500, showlegend=False, xaxis_tickangle=-15)
            st.plotly_chart(fig_box2, use_container_width=True)

    # 底部數據摘要檢查
    with st.expander("🔍 查看目前篩選的原始資料摘要"):
        st.dataframe(filtered_df)
