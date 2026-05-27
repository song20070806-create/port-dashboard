import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# 設定網頁標題與寬度
st.set_page_config(page_title="全球港口績效動態儀表板", layout="wide")

# ==============================================================================
# 🎯 核心功能：雙軌制欄位對齊與全面防崩潰機制
# ==============================================================================
@st.cache_data
def load_and_clean_data():
    file_name = "US_PortCalls_S.csv"
    
    try:
        df = pd.read_csv(file_name)
    except Exception as e:
        st.error(f"❌ 無法讀取 CSV 檔案！請確認 `{file_name}` 是否有正確上傳到 GitHub 同個資料夾下。錯誤訊息: {e}")
        return pd.DataFrame()

    # 剔除自動產生的未命名流水號欄位
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    
    # 建立全新的乾淨資料表
    new_df = pd.DataFrame()
    
    # --- 1. 識別三大文字維度 ---
    # 國家/經濟體 (Economy)
    economy_col = [c for c in df.columns if "economy" in c.lower() or "label" in c.lower() and "vessel" not in c.lower() and "period" not in c.lower()]
    if economy_col:
        new_df['economy_label'] = df[economy_col[0]]
    else:
        new_df['economy_label'] = df.iloc[:, 0] # 位置保底：第 1 欄

    # 船舶類型 (Vessel Type)
    vessel_col = [c for c in df.columns if "vessel" in c.lower()]
    if vessel_col:
        new_df['vessel_type'] = df[vessel_col[0]]
    else:
        new_df['vessel_type'] = df.iloc[:, 1] # 位置保底：第 2 欄

    # 報告期間 (Period)
    period_col = [c for c in df.columns if "period" in c.lower() or "year" in c.lower()]
    if period_col:
        new_df['period'] = df[period_col[0]]
    else:
        new_df['period'] = df.iloc[:, -1] # 位置保底：最後一欄

    # --- 2. 識別六大數值指標 ---
    # 定義我們期望的標準欄位名稱 (Kaggle EDA 規範)
    target_numeric_names = [
        'avg_vessel_age', 'median_time_in_port', 'avg_size_GT', 
        'avg_cargo_capacity_DWT', 'max_size_GT', 'max_cargo_capacity_DWT'
    ]
    
    # 找出 CSV 中所有含有 "_Value" 或者屬於數值欄位的候選者
    value_cols = [c for c in df.columns if "_value" in c.lower() or "value" in c.lower()]
    
    # 如果找不到帶有 value 的欄位，就拿排除掉文字維度後剩下的前 6 個欄位
    if len(value_cols) < 6:
        used_cols = [new_df['economy_label'].name if hasattr(new_df['economy_label'], 'name') else None,
                     new_df['vessel_type'].name if hasattr(new_df['vessel_type'], 'name') else None,
                     new_df['period'].name if hasattr(new_df['period'], 'name') else None]
        value_cols = [c for c in df.columns if c not in used_cols]

    # 精準對齊並強制轉換為數字
    for i, target_name in enumerate(target_numeric_names):
        if i < len(value_cols):
            orig_col = value_cols[i]
            # 把 Kaggle 常見的文字髒資料過濾掉
            s = df[orig_col].astype(str).replace("Not available or not separately reported", pd.NA)
            new_df[target_name] = pd.to_numeric(s, errors='coerce')
        else:
            new_df[target_name] = np.nan

    # --- 3. 缺失值中位數填補與文字清洗 ---
    for col in target_numeric_names:
        median_val = new_df[col].median()
        if pd.isna(median_val):
            median_val = 0.0
        new_df[col] = new_df[col].fillna(median_val)
        
    new_df['economy_label'] = new_df['economy_label'].fillna("Unknown").astype(str).str.strip()
    new_df['vessel_type'] = new_df['vessel_type'].fillna("All_Vessel_Types").astype(str).str.strip()
    new_df['period'] = new_df['period'].fillna("Unknown").astype(str).str.strip()
    
    # 還原 Kaggle 船隻類型的重命名邏輯
    new_df['vessel_type'] = new_df['vessel_type'].replace({'All ships': 'All_Vessel_Types'})
    
    # 過濾掉可能不小心抓到的欄位標題行
    new_df = new_df[new_df['period'] != "Period/Label"]
    new_df = new_df[new_df['economy_label'] != "Economy/Label"]
    
    return new_df

# 執行資料載入
df_cleaned = load_and_clean_data()

# ==============================================================================
# 🎛️ 前端網頁渲染與側邊欄 (全面加上安全阻斷器，防止畫面全白)
# ==============================================================================
if df_cleaned.empty:
    st.warning("⚠️ 資料表目前為空，無法渲染儀表板。請確認上傳的資料集是否有數據。")
else:
    st.sidebar.header("📊 數據篩選中心")

    # 1. 半年度期間篩選器
    all_periods = sorted([x for x in df_cleaned['period'].unique() if x not in ["Unknown", "Period/Label"]])
    if all_periods:
        selected_period = st.sidebar.selectbox("選擇報告期間 (Period)", all_periods, index=len(all_periods)-1)
    else:
        selected_period = "Unknown"

    # 2. 船舶類型篩選器
    all_vessels = sorted([x for x in df_cleaned['vessel_type'].unique() if x != "Vessel type/Label"])
    default_vessels = [v for v in ["All_Vessel_Types", "Container ships", "Liquid bulk carriers"] if v in all_vessels]
    if not default_vessels:
        default_vessels = all_vessels[:2] if len(all_vessels) > 1 else all_vessels

    selected_vessels = st.sidebar.multiselect("選擇船舶類型", all_vessels, default=default_vessels)

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
    
    if not filtered_df.empty and filtered_df['economy_label'].nunique() > 0:
        # 排序讓折線呈現完美梯形降落
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

    # 底部數據摘要檢查
    with st.expander("🔍 檢視當前動態資料集摘要"):
        st.dataframe(filtered_df)
