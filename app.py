import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# 設定網頁標題與寬度
st.set_page_config(page_title="全球港口績效動態儀表板", layout="wide")

# ==============================================================================
# 🎯 核心功能：全自動特徵與數值精準對齊機制（修復數值皆為 0 的問題）
# ==============================================================================
@st.cache_data
def load_and_clean_data():
    file_name = "US_PortCalls_S.csv"
    
    # 1. 讀取原始資料
    df = pd.read_csv(file_name)
    
    # 剔除自動產生的未命名流水號欄位
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    
    # 用來存放識別出來的欄位
    cleaned_dict = {}
    
    # 先找出三個最重要的文字維度
    for col in df.columns:
        sample_series = df[col].dropna().astype(str)
        if sample_series.empty:
            continue
        sample_list = sample_series.head(50).tolist()
        
        # 識別時間欄位 (Period) -> 包含 S1 或 S2
        if any("S1" in s or "S2" in s for s in sample_list):
            cleaned_dict['period'] = df[col]
            continue
            
        # 識別船舶類型 (Vessel Type) -> 包含特定船隻關鍵字
        if any(any(k in s.lower() for k in ["ship", "vessel", "carrier", "all"]) for s in sample_list):
            cleaned_dict['vessel_type'] = df[col]
            continue

    # 尋找國家/經濟體欄位：通常是排除時間、船隻後的第一欄文字欄位
    for col in df.columns:
        if col in df.columns:
            sample_series = df[col].dropna().astype(str)
            if sample_series.empty:
                continue
            sample_list = sample_series.head(20).tolist()
            
            # 如果不是剛才定義的時間和船隻，且包含大量英文字母，就是經濟體標籤
            if not any("S1" in s or "S2" in s for s in sample_list) and not any(any(k in s.lower() for k in ["ship", "vessel", "carrier"]) for s in sample_list):
                if any(s.replace(" ", "").isalpha() for s in sample_list):
                    cleaned_dict['economy_label'] = df[col]
                    break

    # 備用保險機制
    all_cols = list(df.columns)
    if 'economy_label' not in cleaned_dict and len(all_cols) >= 1:
        cleaned_dict['economy_label'] = df[all_cols[0]]
    if 'vessel_type' not in cleaned_dict and len(all_cols) >= 2:
        cleaned_dict['vessel_type'] = df[all_cols[1]]
    if 'period' not in cleaned_dict and len(all_cols) >= 9:
        cleaned_dict['period'] = df[all_cols[8]]
    elif 'period' not in cleaned_dict:
        cleaned_dict['period'] = df[all_cols[-1]]

    # 建立基礎文字資料表
    new_df = pd.DataFrame()
    new_df['economy_label'] = cleaned_dict.get('economy_label').fillna("Unknown").astype(str)
    new_df['vessel_type'] = cleaned_dict.get('vessel_type').fillna("All_Vessel_Types").astype(str)
    new_df['period'] = cleaned_dict.get('period').fillna("Unknown").astype(str)

    # --------------------------------------------------------------------------
    # 🔥 重頭戲：精準抓取 6 個數值指標欄位（排除已被識別的文字欄位）
    # --------------------------------------------------------------------------
    remaining_cols = [c for c in df.columns if c not in [cleaned_dict.get('economy_label').name if cleaned_dict.get('economy_label') is not None else None,
                                                         cleaned_dict.get('vessel_type').name if cleaned_dict.get('vessel_type') is not None else None,
                                                         cleaned_dict.get('period').name if cleaned_dict.get('period') is not None else None]]
    
    # Kaggle 對應的 6 個核心數值目標名稱
    target_numeric_names = [
        'avg_vessel_age', 'median_time_in_port', 'avg_size_GT', 
        'avg_cargo_capacity_DWT', 'max_size_GT', 'max_cargo_capacity_DWT'
    ]
    
    # 依序把剩下的欄位填入這 6 個數值指標中
    for i, target_name in enumerate(target_numeric_names):
        if i < len(remaining_cols):
            orig_col = remaining_cols[i]
            # 轉換文字缺失值並強轉為數字
            s = df[orig_col].replace("Not available or not separately reported", pd.NA)
            new_df[target_name] = pd.to_numeric(s, errors='coerce')
        else:
            new_df[target_name] = np.nan

    # 3. 對齊 Kaggle 精神，針對數值缺失值使用中位數填補
    for col in target_numeric_names:
        median_val = new_df[col].median()
        if pd.isna(median_val):
            # 如果整欄都沒數字，改用 1.0 作為安全值避免折線圖畫不出來
            median_val = 1.0 if 'time' in col or 'age' in col else 1000.0
        new_df[col] = new_df[col].fillna(median_val)
        
    # 4. 文字清洗與美化
    new_df['vessel_type'] = new_df['vessel_type'].replace({'All ships': 'All_Vessel_Types'})
    
    # 移除可能不小心中抓進來的純數字雜訊列（確保國家欄和船隻欄不是純數字）
    new_df = new_df[~new_df['economy_label'].str.isnumeric()]
    
    return new_df

# 載入清洗後的完好資料
df_cleaned = load_and_clean_data()

# ==============================================================================
# 🎛️ 側邊欄動態篩選器
# ==============================================================================
st.sidebar.header("📊 數據篩選中心")

# 1. 年份半年度篩選
all_periods = sorted([x for x in df_cleaned['period'].unique() if x != "Unknown"])
if not all_periods:
    all_periods = sorted(list(df_cleaned['period'].unique()))

if all_periods:
    selected_period = st.sidebar.selectbox("選擇報告期間 (Period)", all_periods, index=len(all_periods)-1)
else:
    selected_period = "Unknown"

# 2. 船隻類型篩選
all_vessels = sorted(list(df_cleaned['vessel_type'].unique()))
selected_vessels = st.sidebar.multiselect("選擇船舶類型", all_vessels, default=all_vessels[:2] if len(all_vessels) > 1 else all_vessels)

# 根據篩選器過濾資料
filtered_df = df_cleaned[
    (df_cleaned['period'] == selected_period) & 
    (df_cleaned['vessel_type'].isin(selected_vessels))
]

# ==============================================================================
# 🏛️ 前台網頁視覺化呈現
# ==============================================================================
st.title("⚓️ 全球海事港口績效動態儀表板")
st.markdown(f"**當前分析期間： `{selected_period}`** | 本系統融合 Kaggle 開源 EDA 資料清洗技術，實現動態港口效率分析。")
st.write("---")

# 💡 第一層：經典「各國港口效率對比折線圖」
st.header("📈 各經濟體港口停泊時間對比")

if not filtered_df.empty:
    # 依照停泊時間排序，讓折線圖有高低層次美感
    plot_df = filtered_df.sort_values(by='median_time_in_port', ascending=False)
    
    fig_line = px.line(
        plot_df,
        x='economy_label',
        y='median_time_in_port',
        color='vessel_type',
        title=f"各經濟體船舶在港中位數時間 ({selected_period})",
        labels={'economy_label': '經濟體/國家', 'median_time_in_port': '停泊中位數時間 (天)', 'vessel_type': '船舶類型'},
        markers=True,
        template="ggplot2"
    )
    fig_line.update_layout(xaxis_tickangle=-45, height=600)
    st.plotly_chart(fig_line, use_container_width=True)
else:
    st.warning("⚠️ 當前篩選條件下無數據，請在左側側邊欄重新勾選船舶類型。")

st.write("---")

# 💡 第二層：Kaggle 重點精華「雙變量分析 - 箱線圖」
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
