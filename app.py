import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# 設定網頁標題與寬度
st.set_page_config(page_title="全球港口績效動態儀表板", layout="wide")

# ==============================================================================
# 🎯 核心功能：安全長度對齊與全面清洗（解決 ValueError: Length mismatch）
# ==============================================================================
@st.cache_data
def load_and_clean_data():
    file_name = "US_PortCalls_S.csv"
    try:
        df = pd.read_csv(file_name)
    except Exception as e:
        st.error(f"❌ 無法讀取 CSV 檔案：{e}")
        return pd.DataFrame()

    # 1. 剔除未命名的流水號欄位，確保欄位乾淨
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    
    # 如果資料根本不夠，直接返回
    if df.shape[0] == 0 or df.shape[1] < 3:
        return pd.DataFrame()

    # 2. 一字不差地建立基礎乾淨資料表，保證列數跟原始 df 絕對完全一致！
    new_df = pd.DataFrame(index=df.index)
    
    # 3. 填入三大基本文字維度（改用安全指派，不單獨過濾避免長度錯開）
    new_df['economy_label'] = df.iloc[:, 0].astype(str).str.strip()
    new_df['vessel_type'] = df.iloc[:, 1].astype(str).str.strip()
    
    # 尋找時間欄位（如果第 9 欄在範圍內就用第 9 欄，否則用最後一欄）
    if df.shape[1] >= 9:
        new_df['period'] = df.iloc[:, 8].astype(str).str.strip()
    else:
        new_df['period'] = df.iloc[:, -1].astype(str).str.strip()

    # 4. 填入六大核心數值指標
    target_numeric_names = [
        'avg_vessel_age', 'median_time_in_port', 'avg_size_GT', 
        'avg_cargo_capacity_DWT', 'max_size_GT', 'max_cargo_capacity_DWT'
    ]
    
    for i, target_name in enumerate(target_numeric_names):
        col_idx = 2 + i  # 數值欄位從第 3 欄（索引 2）開始
        if col_idx < df.shape[1]:
            # 安全轉換：把文字雜訊轉成 NaN，保持整欄長度不變
            s = df.iloc[:, col_idx].astype(str).replace("Not available or not separately reported", pd.NA)
            new_df[target_name] = pd.to_numeric(s, errors='coerce')
        else:
            new_df[target_name] = np.nan

    # 5. 統一填補數值缺失值
    for col in target_numeric_names:
        median_val = new_df[col].median()
        if pd.isna(median_val):
            median_val = 0.0
        new_df[col] = new_df[col].fillna(median_val)
        
    # 6. 文字美化與「全表格安全過濾」
    new_df['vessel_type'] = new_df['vessel_type'].replace({'All ships': 'All_Vessel_Types'})
    
    # 💡 絕招：在最後一步，用條件篩選直接拿掉標題雜訊列，這樣絕對不會造成欄位長度不一！
    mask = (
        (~new_df['period'].str.contains('Period', case=False, na=False)) & 
        (~new_df['economy_label'].str.contains('Economy', case=False, na=False))
    )
    new_df = new_df[mask].reset_index(drop=True)
    
    return new_df

df_cleaned = load_and_clean_data()

# ==============================================================================
# 🎛️ 前端網頁渲染與側邊欄
# ==============================================================================
if df_cleaned.empty or 'period' not in df_cleaned.columns:
    st.error("⚠️ 資料載入失敗，表格為空或結構不正確。")
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
        default_vessels = all_vessels[:2] if len(all_vessels) > 0 else all_vessels

    selected_vessels = st.sidebar.multiselect("選擇船舶類型", all_vessels, default=default_vessels)

    # 3. 限制顯示的國家數量
    max_countries = st.sidebar.slider("畫面上顯示前幾名效率排行國家", min_value=5, max_value=40, value=15)

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
    
    if not filtered_df.empty:
        plot_df = filtered_df.sort_values(by='median_time_in_port', ascending=False).head(max_countries)
        
        try:
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
            
            max_y = float(plot_df['median_time_in_port'].max()) if not plot_df['median_time_in_port'].empty else 5.0
            fig_line.update_layout(
                xaxis_tickangle=-45, 
                height=600,
                yaxis_range=[0, max_y * 1.3]
            )
            st.plotly_chart(fig_line, use_container_width=True)
        except Exception as plot_error:
            st.error(f"❌ 渲染折線圖時發生錯誤: {plot_error}")
    else:
        st.warning("⚠️ 當前篩選條件下無數據，請在左側側邊欄重新勾選船舶類型。")

    st.write("---")

    # 💡 第二層：雙變量統計箱線圖
    st.header("📊 進階統計：船舶類型 vs 港口核心指標分佈 (Boxplot)")

    tab1, tab2 = st.tabs(["⏳ 在港停泊時間分佈", "🚢 船舶平均總噸位(GT)分佈"])

    with tab1:
        if not filtered_df.empty:
            try:
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
            except Exception as e:
                st.error(f"無法渲染停泊時間箱線圖: {e}")

    with tab2:
        if not filtered_df.empty:
            try:
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
            except Exception as e:
                st.error(f"無法渲染噸位箱線圖: {e}")

    # 底部數據檢查器
    with st.expander("🔍 檢視當前動態資料集摘要"):
        st.dataframe(filtered_df)
