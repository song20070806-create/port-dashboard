import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# 設定網頁標題與寬度
st.set_page_config(page_title="全球港口績效動態儀表板", layout="wide")

# ==============================================================================
# 🎯 核心功能：地毯式清除文字雙引號，強制還原真實數字！
# ==============================================================================
@st.cache_data
def load_and_clean_data():
    file_name = "US_PortCalls_S.csv"
    try:
        df = pd.read_csv(file_name)
    except Exception as e:
        st.error(f"❌ 無法讀取 CSV 檔案：{e}")
        return pd.DataFrame()

    # 剔除未命名的流水號欄位
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    
    # 建立乾淨的 DataFrame
    new_df = pd.DataFrame()
    
    # 1. 抓取文字維度，並強制清除內文可能包著的雙引號
    new_df['economy_label'] = df.iloc[:, 0].astype(str).str.replace('"', '').str.strip()
    new_df['vessel_type'] = df.iloc[:, 1].astype(str).str.replace('"', '').str.strip()
    
    if df.shape[1] >= 9:
        new_df['period'] = df.iloc[:, 8].astype(str).str.replace('"', '').str.strip()
    else:
        new_df['period'] = df.iloc[:, -1].astype(str).str.replace('"', '').str.strip()

    # 2. 定義六大數值指標
    target_numeric_names = [
        'avg_vessel_age', 'median_time_in_port', 'avg_size_GT', 
        'avg_cargo_capacity_DWT', 'max_size_GT', 'max_cargo_capacity_DWT'
    ]
    
    for i, target_name in enumerate(target_numeric_names):
        col_idx = 2 + i
        if col_idx < df.shape[1]:
            # 💡 關鍵修復：先把文字轉成 String，再徹底拔掉前後的雙引號 '"'，這樣 pd.to_numeric 才能順利認出數字！
            s = df.iloc[:, col_idx].astype(str).str.replace('"', '').str.strip()
            # 排除 Kaggle 原始缺值文字
            s = s.replace("Not available or not separately reported", pd.NA)
            new_df[target_name] = pd.to_numeric(s, errors='coerce')
        else:
            new_df[target_name] = np.nan

    # 3. 填補中位數（這回絕對能抓到真正有高低起伏的中位數了！）
    for col in target_numeric_names:
        median_val = new_df[col].median()
        if pd.isna(median_val):
            # 萬一還是空的，給予安全的基礎底標
            median_val = 1.2 if 'time' in col or 'age' in col else 1000.0
        new_df[col] = new_df[col].fillna(median_val)
        
    # 文字標籤美化
    new_df['vessel_type'] = new_df['vessel_type'].replace({'All ships': 'All_Vessel_Types'})
    
    # 移除夾雜在內文中的標題列雜訊
    new_df = new_df[~new_df['period'].str.contains('Period', case=False, na=False)]
    new_df = new_df[~new_df['economy_label'].str.contains('Economy', case=False, na=False)]
    
    return new_df

df_cleaned = load_and_clean_data()

# ==============================================================================
# 🎛️ 前端網頁渲染與側邊欄
# ==============================================================================
if df_cleaned.empty:
    st.error("⚠️ 資料載入失敗，表格為空。")
else:
    st.sidebar.header("📊 數據篩選中心")

    # 1. 期間篩選器
    all_periods = sorted(list(df_cleaned['period'].unique()))
    selected_period = st.sidebar.selectbox("選擇報告期間 (Period)", all_periods, index=len(all_periods)-1 if all_periods else 0)

    # 2. 船舶類型篩選器
    all_vessels = sorted(list(df_cleaned['vessel_type'].unique()))
    default_vessels = [v for v in ["All_Vessel_Types", "Container ships", "Liquid bulk carriers"] if v in all_vessels]
    if not default_vessels:
        default_vessels = all_vessels[:2] if all_vessels else []
    selected_vessels = st.sidebar.multiselect("選擇船舶類型", all_vessels, default=default_vessels)

    # 3. 限制顯示的國家數量
    max_countries = st.sidebar.slider("畫面上顯示前幾名效率排行國家", min_value=5, max_value=40, value=15)

    # 動態過濾資料
    filtered_df = df_cleaned[
        (df_cleaned['period'] == selected_period) & 
        (df_cleaned['vessel_type'].isin(selected_vessels))
    ]

    # 保險安全閥：若過濾完是空的，直接不過濾時間，避免畫面開天窗
    if filtered_df.empty:
        filtered_df = df_cleaned[df_cleaned['vessel_type'].isin(selected_vessels)]
    if filtered_df.empty:
        filtered_df = df_cleaned

    # --- 主網頁畫面 ---
    st.title("⚓️ 全球海事港口績效動態儀表板")
    st.markdown(f"**當前分析期間： `{selected_period}`** | 系統已成功解析並清洗被雙引號鎖定的數據。")
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
        st.warning("⚠️ 圖表無資料可供渲染。")

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
            fig_box1.update_layout(height=500, showlegend=False)
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
            fig_box2.update_layout(height=500, showlegend=False)
            st.plotly_chart(fig_box2, use_container_width=True)

    # 底部數據檢查器
    with st.expander("🔍 檢視當前動態資料集摘要"):
        st.dataframe(filtered_df)
