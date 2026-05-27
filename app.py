import streamlit as st  # 修正：之前手誤打成 as pd，導致 NameError
import pandas as pd
import numpy as np
import plotly.express as px

# 設定網頁標題與寬度 (這行現在不會報錯了！)
st.set_page_config(page_title="全球港口績效動態儀表板", layout="wide")

# ==============================================================================
# 🎯 核心融合：採用 Kaggle EDA 筆記本的專業資料清洗邏輯
# ==============================================================================
@st.cache_data
def load_and_clean_data():
    # 修正：根據 image_6293fc.png 的報錯提示，對齊你 GitHub 上的真實檔名
    file_name = "US_PortCalls_S.csv" 
    df = pd.read_csv(file_name, index_col=0)
    
    # 2. 處理偽裝成文字的缺失值（對齊 Kaggle `In [2]` 邏輯）
    placeholder = "Not available or not separately reported"
    df.replace(placeholder, pd.NA, inplace=True)
    
    # 3. 強制將數值欄位轉為純數字（對齊 Kaggle 清洗步驟 3）
    value_cols = [col for col in df.columns if "_Value" in col]
    for col in value_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
        
    # 4. 填補中位數：低於 50% 缺失的欄位用中位數補齊（對齊 Kaggle 清洗步驟 6）
    target_value_col = "Median time spent in port (days)_Value"
    if target_value_col in df.columns:
        median_val = df[target_value_col].median()
        df[target_value_col] = df[target_value_col].fillna(median_val)
    
    # 5. 欄位親民化命名（對齊 Kaggle 清洗步驟 7）
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
# 預設勾選全部船隻
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

# 💡 第一層：昨天的經典「各國港口效率對比折線圖」
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
        template="ggplot2"  # 沿用 Kaggle 作者最愛的 ggplot 風格！
    )
    fig_line.update_layout(xaxis_tickangle=-45, height=600)
    st.plotly_chart(fig_line, use_container_width=True)
else:
    st.warning("⚠️ 當前篩選條件下無數據，請在左側側邊欄重新勾選船舶類型。")

st.write("---")

# 💡 第二層：Kaggle 精華「雙變量分析 - 船舶類型分佈箱線圖」的互動升級版
st.header("📊 進階統計：不同船舶類型的港口停泊時間分佈 (Boxplot)")
st.markdown("""
**💡 報告亮點說明（上台報告直接念這段）：**
這個箱線圖（Boxplot）是本研究的關鍵科學分析。我們將 Kaggle 筆記本中的靜態雙變量統計（Bivariate Analysis）升級為動態版本。
透過箱線圖，我們可以觀察到不同船種的**中位數、上下四分位數以及極端異常值**。例如：貨櫃船與天然氣船通常週轉極快，而散裝貨輪的停留時間分佈則較廣。
""")

if not filtered_df.empty:
    fig_box = px.box(
        filtered_df,
        x='vessel_type',
        y='median_time_in_port',
        color='vessel_type',
        title=f"船舶類型 vs 港口停泊時間統計分佈 ({selected_period})",
        labels={'vessel_type': '船舶類型', 'median_time_in_port': '在港時間 (天)'},
        points="all",  # 把每個真實的數據點也點出來，看起來超專業
        template="ggplot2"
    )
    fig_box.update_layout(height=500, showlegend=False)
    st.plotly_chart(fig_box, use_container_width=True)
    
    # 底部附帶小數據表，增加專業感
    with st.expander("🔍 檢視當前動態資料集摘要"):
        st.dataframe(filtered_df[['economy_label', 'vessel_type', 'median_time_in_port', 'avg_vessel_age', 'period']])
