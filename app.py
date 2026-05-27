import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# 設定網頁標題與寬度
st.set_page_config(page_title="全球港口績效動態儀表板", layout="wide")

# ==============================================================================
# 🎯 核心功能：絕對位置抓取與清洗邏輯
# ==============================================================================
@st.cache_data
def load_and_clean_data():
    file_name = "US_PortCalls_S.csv"
    try:
        df = pd.read_csv(file_name)
    except Exception as e:
        st.error(f"❌ 無法讀取 CSV 檔案：{e}")
        return pd.DataFrame()

    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    new_df = pd.DataFrame()
    
    try:
        new_df['economy_label'] = df.iloc[:, 0]  # 第 1 欄：國家
        new_df['vessel_type'] = df.iloc[:, 1]   # 第 2 欄：船隻類型
        
        target_numeric_names = [
            'avg_vessel_age', 'median_time_in_port', 'avg_size_GT', 
            'avg_cargo_capacity_DWT', 'max_size_GT', 'max_cargo_capacity_DWT'
        ]
        
        for i, target_name in enumerate(target_numeric_names):
            col_idx = 2 + i
            if col_idx < df.shape[1]:
                s = df.iloc[:, col_idx].astype(str).replace("Not available or not separately reported", pd.NA)
                new_df[target_name] = pd.to_numeric(s, errors='coerce')
            else:
                new_df[target_name] = np.nan
                
        new_df['period'] = df.iloc[:, -1]  # 最後一欄：時間
        
    except Exception as e:
        st.error(f"❌ 解析 CSV 欄位出錯: {e}")
        return pd.DataFrame()

    # 缺失值填補
    for col in target_numeric_names:
        median_val = new_df[col].median()
        if pd.isna(median_val):
            median_val = 0.0
        new_df[col] = new_df[col].fillna(median_val)
        
    new_df['economy_label'] = new_df['economy_label'].fillna("Unknown").astype(str).str.strip()
    new_df['vessel_type'] = new_df['vessel_type'].fillna("All_Vessel_Types").astype(str).str.strip()
    new_df['period'] = new_df['period'].fillna("Unknown").astype(str).str.strip()
    
    new_df['vessel_type'] = new_df['vessel_type'].replace({'All ships': 'All_Vessel_Types'})
    new_df = new_df[~new_df['period'].str.contains('Period', case=False, na=False)]
    new_df = new_df[~new_df['economy_label'].str.contains('Economy', case=False, na=False)]
    
    return new_df

df_cleaned = load_and_clean_data()

# ==============================================================================
# 🎛️ 前端網頁渲染與側邊欄
# ==============================================================================
if df_cleaned.empty:
    st.warning("⚠️ 資料表目前為空，無法渲染儀表板。")
else:
    st.sidebar.header("📊 數據篩選中心")

    # 1. 半年度期間篩選器
    all_periods = sorted([x for x in df_cleaned['period'].unique() if x != "Unknown"])
    if all_periods:
        selected_period = st.sidebar.selectbox("選擇報告期間 (Period)", all_periods, index=len(all_periods)-1)
    else:
        selected_period = "Unknown"

    # 2. 船舶類型篩選器
    all_vessels = sorted(list(df_cleaned['vessel_type'].unique()))
    default_vessels = [v for v in ["All_Vessel_Types", "Container ships", "Liquid bulk carriers"] if v in all_vessels]
    if not default_vessels:
        default_vessels = all_vessels[:2] if len(all_vessels) > 1 else all_vessels

    selected_vessels = st.sidebar.multiselect("選擇船舶類型", all_vessels, default=default_vessels)

    # 3. 🎯 視覺優化核心：控制畫面上要顯示幾個國家（避免塞滿 100 多個國家看起來像直線）
    max_countries = st.sidebar.slider("畫面上顯示前幾名效率排行國家", min_value=5, max_value=30, value=15)

    # 動態過濾資料
    filtered_df = df_cleaned[
        (df_cleaned['period'] == selected_period) & 
        (df_cleaned['vessel_type'].isin(selected_vessels))
    ]

    # --- 主網頁畫面 ---
    st.title("⚓️ 全球海事港口績效動態儀表板")
    st.markdown(f"**當前分析期間： `{selected_period}`** | 本系統融合 Kaggle 開源 EDA 資料清洗技術，實現動態港口效率分析。")
    st.write("---")

    # 💡 第一層：折線圖
    st.header("📈 各經濟體港口停泊時間對比")
    st.markdown(f"以下圖表呈現停泊時間最長的 **前 {max_countries} 個國家/經濟體**，您可以清楚觀察到數據高低的波動層次。")
    
    if not filtered_df.empty:
        # 排序並切出前 N 個國家，讓圖表有高低落差的美感！
        plot_df = filtered_df.sort_values(by='median_time_in_port', ascending=False).head(max_countries)
        
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
        
        # 🚀 視覺微調：強制讓 Y 軸從 0 開始，這樣波動就會非常漂亮，不會擠在 1.0 的死線區
        max_y = plot_df['median_time_in_port'].max()
        fig_line.update_layout(
            xaxis_tickangle=-45, 
            height=600,
            yaxis_range=[0, max_y * 1.2]
        )
        st.plotly_chart(fig_line, use_container_width=True)
    else:
        st.info("💡 請在左側勾選「船舶類型」來啟動折線圖分析。")

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
                title=f"不同船舶類型的港口停泊時間統計分佈 ({selected_period})",
                labels={'vessel_type': '船舶類型', 'median_time_in_port': '在港時間 (天)'},
                points="all",
                template="ggplot2"
            )
            fig_box1.update_layout(height=500, showlegend=False)
            st.plotly_chart(fig_box1, use_container_width=True)

    with tab2:
        if not filtered_df.empty:
            fig_box2 = px.box(
                filtered_df,
                x='vessel_type',
                y='avg_size_GT',
                color='vessel_type',
                title=f"不同船舶類型的平均總噸位 (GT) 統計分佈 ({selected_period})",
                labels={'vessel_type': '船舶類型', 'avg_size_GT': '平均總噸位 (GT)'},
                points="all",
                template="ggplot2"
            )
            fig_box2.update_layout(height=500, showlegend=False)
            st.plotly_chart(fig_box2, use_container_width=True)

    # 底部數據檢查器
    with st.expander("🔍 檢視當前動態資料集摘要"):
        st.dataframe(filtered_df)
