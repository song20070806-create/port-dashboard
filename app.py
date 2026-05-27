import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# 設定網頁標題與寬度
st.set_page_config(page_title="全球港口績效動態儀表板", layout="wide")

# ==============================================================================
# 🎯 核心融合：最穩定的精準資料清洗邏輯（徹底解決變數與欄位衝突）
# ==============================================================================
@st.cache_data
def load_and_clean_data():
    # 讀取你的真實資料檔
    file_name = "US_PortCalls_S.csv"
    df = pd.read_csv(file_name, index_col=0)
    
    # 【超級修正案】：直接手動抓取我們需要的 9 個核心欄位，徹底繞開 Kaggle 程式碼計算缺失值的 Bug
    # 這 9 個欄位是畫折線圖、箱線圖的所有精華
    keep_cols = [
        "Economy/Label",
        "Vessel type/Label",
        "Average age of vessels_Value",
        "Median time spent in port (days)_Value",
        "Average size (GT) of vessels_Value",
        "Average cargo carrying capacity (DWT) of vessels_Value",
        "Maximum size (GT) of vessels_Value",
        "Maximum cargo carrying capacity (DWT) of vessels_Value",
        "Period/Label"
    ]
    
    # 只保留這 9 個必要的欄位
    df = df[keep_cols].copy()
    
    # 2. 處理偽裝成文字的缺失值（對齊 Kaggle 邏輯）
    placeholder = "Not available or not separately reported"
    df.replace(placeholder, pd.NA, inplace=True)
    
    # 3. 強制將數值欄位轉為純數字
    value_cols = [
        "Average age of vessels_Value",
        "Median time spent in port (days)_Value",
        "Average size (GT) of vessels_Value",
        "Average cargo carrying capacity (DWT) of vessels_Value",
        "Maximum size (GT) of vessels_Value",
        "Maximum cargo carrying capacity (DWT) of vessels_Value"
    ]
    for col in value_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
        
    # 4. 填補中位數（對齊 Kaggle 精髓：用該欄位的中位數補齊空缺處）
    for col in value_cols:
        median_val = df[col].median()
        df[col] = df[col].fillna(median_val)
    
    # 5. 精準命名 9 大親民化欄位（長度 100% 完美匹配！）
    df.columns = [
        'economy_label', 'vessel_type', 'avg_vessel_age', 'median_time_in_port', 
        'avg_size_GT', 'avg_cargo_capacity_DWT', 'max_size_GT', 'max_cargo_capacity_DWT', 'period'
    ]
    
    # 6. 修正特定文字標籤，使其在圖表上更美觀
    df['vessel_type'] = df['vessel_type'].replace({'All ships': 'All_Vessel_Types'})
    
    return df

# 載入清洗完畢的乾淨資料
df_cleaned = load_and_clean_data()

# ==============================================================================
# 🎛️ 側邊欄動態篩選器
# ==============================================================================
st.sidebar.header("📊 數據篩選中心")

# 1. 年份半年度篩選（Period）
all_periods = sorted(df_cleaned['period'].unique())
selected_period = st.sidebar.selectbox("選擇報告期間 (Period)", all_periods, index=len(all_periods)-1)

# 2. 船隻類型篩選（Vessel Type）
all_vessels = df_cleaned['vessel_type'].unique().tolist()
selected_vessels = st.sidebar.multiselect("選擇船舶類型", all_vessels, default=all_vessels)

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
st.markdown("您可以透過左側篩選不同的船舶類型，觀察各國港口在該期間的綜合週轉效率。")

if not filtered_df.empty:
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

# 💡 第二層：Kaggle 重點精華「雙變量分析 (Bivariate Analysis) - 箱線圖」
st.header("📊 進階統計：船舶類型 vs 港口核心指標分佈 (Boxplot)")
st.markdown("這裡完美還原並升級了 Kaggle 作者針對 `median_time_in_port` 與 `avg_size_GT` 所作的雙變量箱線圖分析。")

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
        st.info("💡 **學術洞察**：貨櫃船（Container ships）與天然氣船（LNG carriers）的在港時間顯著較短，反映其極高的港口自動化與週轉效率。")

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
        st.info("💡 **學術洞察**：大型散裝貨輪與貨櫃船的噸位分佈極廣，這與全球主要深水港口的硬體吃水限制密切相關。")

# 底部數據檢查器
with st.expander("🔍 檢視當前動態資料集摘要"):
    st.dataframe(filtered_df[['economy_label', 'vessel_type', 'median_time_in_port', 'avg_size_GT', 'period']])
