import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# 設定網頁標題與寬度
st.set_page_config(page_title="全球港口績效動態儀表板", layout="wide")

# ==============================================================================
# 🎯 核心融合：全自動特徵辨識演算法（彻底根除所有欄位命名/錯位帶來的無資料問題）
# ==============================================================================
@st.cache_data
def load_and_clean_data():
    file_name = "US_PortCalls_S.csv"
    
    # 1. 讀取 CSV
    df = pd.read_csv(file_name)
    
    # 如果最左邊被 Pandas 讀出一個名為 "Unnamed" 的流水號欄位，直接把它丟掉
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    
    cleaned_dict = {}
    numeric_candidates = []
    
    # 2. 用「資料內容特徵」來通靈抓欄位，完全無視欄位英文叫什麼！
    for col in df.columns:
        # 將該欄內容轉成字串，並過濾掉空值來做樣品檢查
        sample_series = df[col].dropna().astype(str)
        if sample_series.empty:
            continue
            
        sample_list = sample_series.head(50).tolist()
        combined_samples = " ".join(sample_list)
        
        # 特徵 A：如果這欄包含 "S1" 或 "S2"，那它絕對是時間報告期間 (Period)
        if any("S1" in s or "S2" in s for s in sample_list):
            cleaned_dict['period'] = df[col]
            continue
            
        # 特徵 B：如果是文字，且裡面包含常見的船隻字眼（或 All ships），就是船舶類型
        if any(any(k in s.lower() for k in ["ship", "vessel", "carrier", "all"]) for s in sample_list):
            cleaned_dict['vessel_type'] = df[col]
            continue
            
        # 特徵 C：如果是文字，且不是船、不是時間，那它高機率就是國家/經濟體 (Economy)
        # 我們檢查它的平均字串長度，通常國家名字會比代碼長
        is_alpha_text = sample_series.str.replace(" ", "").str.isalpha().all()
        if not is_alpha_text and any(s.isalpha() for s in sample_list):
            is_alpha_text = True
            
        if 'vessel_type' not in cleaned_dict and 'period' not in cleaned_dict:
            # 如果目前還沒抓到國家，暫時當作國家候選
            cleaned_dict['economy_label'] = df[col]
            
        # 特徵 D：收集所有可能是數字的欄位（包含混雜著 "Not available" 雜訊的數值欄位）
        cleaned_dict[col] = df[col]
        numeric_candidates.append(col)

    # 如果用特徵沒抓滿三個核心文字欄位，則依據前三欄順序強行補位
    all_cols = list(df.columns)
    if 'economy_label' not in cleaned_dict and len(all_cols) >= 1:
        cleaned_dict['economy_label'] = df[all_cols[0]]
    if 'vessel_type' not in cleaned_dict and len(all_cols) >= 2:
        cleaned_dict['vessel_type'] = df[all_cols[1]]
    if 'period' not in cleaned_dict and len(all_cols) >= 9:
        cleaned_dict['period'] = df[all_cols[8]]
    elif 'period' not in cleaned_dict:
        cleaned_dict['period'] = df[all_cols[-1]]

    # 建立最終乾淨的 DataFrame
    new_df = pd.DataFrame()
    new_df['economy_label'] = cleaned_dict.get('economy_label', pd.Series(["Unknown"] * len(df)))
    new_df['vessel_type'] = cleaned_dict.get('vessel_type', pd.Series(["All_Vessel_Types"] * len(df)))
    new_df['period'] = cleaned_dict.get('period', pd.Series(["Unknown"] * len(df)))
    
    # 處理數值欄位：對齊當初 Kaggle 的 6 大指標命名
    target_numeric_names = [
        'avg_vessel_age', 'median_time_in_port', 'avg_size_GT', 
        'avg_cargo_capacity_DWT', 'max_size_GT', 'max_cargo_capacity_DWT'
    ]
    
    # 篩選出真正的數值列候選人（排除我們剛剛抓走的國家、船隻和時間）
    used_text_cols = [new_df['economy_label'].name, new_df['vessel_type'].name, new_df['period'].name]
    actual_num_candidates = [c for c in numeric_candidates if c not in [df.columns[0], df.columns[1], df.columns[-1]]]
    
    # 將找到的數值欄位一一填入
    for i, target_name in enumerate(target_numeric_names):
        if i < len(actual_num_candidates):
            orig_col = actual_num_candidates[i]
            # 轉換文字缺失值為真正的 NaN
            s = df[orig_col].replace("Not available or not separately reported", pd.NA)
            new_df[target_name] = pd.to_numeric(s, errors='coerce')
        else:
            new_df[target_name] = 0.0

    # 3. 填補中位數（對齊 Kaggle 精神）
    for col in target_numeric_names:
        median_val = new_df[col].median()
        if pd.isna(median_val):
            median_val = 0
        new_df[col] = new_df[col].fillna(median_val)
        
    # 4. 美化船舶文字標籤
    new_df['vessel_type'] = new_df['vessel_type'].fillna("Unknown").astype(str)
    new_df['vessel_type'] = new_df['vessel_type'].replace({'All ships': 'All_Vessel_Types'})
    new_df['period'] = new_df['period'].fillna("Unknown").astype(str)
    new_df['economy_label'] = new_df['economy_label'].fillna("Unknown").astype(str)
    
    return new_df

# 載入清洗完畢的乾淨資料
df_cleaned = load_and_clean_data()

# ==============================================================================
# 🎛️ 側邊欄動態篩選器
# ==============================================================================
st.sidebar.header("📊 數據篩選中心")

# 1. 年份半年度篩選（Period）
all_periods = sorted([x for x in df_cleaned['period'].unique() if x != "Unknown"])
if not all_periods:
    all_periods = sorted(list(df_cleaned['period'].unique()))

if all_periods:
    selected_period = st.sidebar.selectbox("選擇報告期間 (Period)", all_periods, index=len(all_periods)-1)
else:
    selected_period = "Unknown"

# 2. 船隻類型篩選（Vessel Type）
all_vessels = sorted(list(df_cleaned['vessel_type'].unique()))
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
