import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# 設定網頁基本組態
st.set_page_config(page_title="全球港口績效動態儀表板", layout="wide")

def load_and_clean_real_data():
    file_name = "US_PortCalls_S.csv"
    try:
        # 讀取 CSV
        df = pd.read_csv(file_name, encoding='utf-8-sig')
    except Exception as e:
        st.error(f"❌ 無法讀取 CSV 檔案：{e}")
        return pd.DataFrame()

    if df.empty:
        return pd.DataFrame()

    # 拔除所有欄位名稱的前後空格
    df.columns = df.columns.str.strip()
    
    new_df = pd.DataFrame()
    
    # 🎯 根據 debug 畫面呈現的精準欄位名稱進行抓取
    try:
        new_df['period'] = df['Period'].astype(str).str.strip()
        new_df['period_label'] = df['Period Label'].astype(str).str.strip()
        new_df['economy_label'] = df['Economy Label'].astype(str).str.strip()
        new_df['vessel_type'] = df['CommercialMarket Label'].astype(str).str.strip()
        
        # 處理數值欄位 (港口停泊時間)
        s_time = df['Median time in port (days)'].astype(str).str.replace('"', '').str.strip()
        s_time = s_time.replace(["Not available or not separately reported", "nan", "NaN", "null", ""], np.nan)
        new_df['median_time_in_port'] = pd.to_numeric(s_time, errors='coerce')
        
        # 處理數值欄位 (船舶平均總噸位 GT)
        # 備註：若您 CSV 後方有 Average size GT 相關欄位，此處採自動搜字串或保底位置抓取
        gt_cols = [c for c in df.columns if "size" in c.lower() or "gt" in c.lower()]
        if gt_cols:
            s_gt = df[gt_cols[0]].astype(str).str.replace('"', '').str.strip()
            s_gt = s_gt.replace(["Not available or not separately reported", "nan", "NaN", "null", ""], np.nan)
            new_df['avg_size_GT'] = pd.to_numeric(s_gt, errors='coerce')
        else:
            new_df['avg_size_GT'] = 0  # 若無則給予保底 0
            
    except Exception as e:
        st.error(f"❌ 欄位對齊失敗，請檢查名稱是否相符。錯誤: {e}")
        return pd.DataFrame()

    # 🛑 核心過濾：剔除重複的標題列、空值，以及「World」這個總計項（只留個別國家）
    new_df = new_df[~new_df['period'].str.contains('period', case=False, na=False)]
    new_df = new_df[~new_df['economy_label'].str.contains('World|Economy', case=False, na=False)]
    
    # 刪除時間為空值的列
    new_df = new_df.dropna(subset=['median_time_in_port']).reset_index(drop=True)
    
    return new_df

# 強制每次載入重新讀取
df_cleaned = load_and_clean_real_data()

# ==============================================================================
# 🎛️ 前端介面渲染
# ==============================================================================
st.title("⚓️ 全球海事港口績效動態儀表板")

if df_cleaned.empty:
    st.error("⚠️ 資料集清洗後為空。請確認 CSV 是否正確過濾。")
else:
    st.sidebar.header("📊 數據篩選中心")

    # 1. 選擇報告期間 (使用 Period 欄位如 2018S01)
    all_periods = sorted(list(df_cleaned['period'].unique()))
    selected_period = st.sidebar.selectbox("選擇報告期間 (Period)", all_periods, index=0)
    
    period_df = df_cleaned[df_cleaned['period'] == selected_period]

    # 2. 選擇船舶類型
    all_vessels = sorted(list(period_df['vessel_type'].unique()))
    selected_vessels = st.sidebar.multiselect("選擇船舶類型", all_vessels, default=all_vessels)

    # 3. 顯示國家數量排行
    max_countries = st.sidebar.slider("顯示國家數量 (依停泊時間排行)", min_value=5, max_value=40, value=15)

    # 最終過濾後的資料
    filtered_df = period_df[period_df['vessel_type'].isin(selected_vessels)]

    # 防止使用者把船型全部取消勾選導致崩潰的保底機制
    if filtered_df.empty:
        filtered_df = period_df

    st.markdown(f"**當前分析期間： `{selected_period}`**")
    st.write("---")

    # 📊 第一層：各經濟體港口停泊時間對比長條圖
    st.header("📊 各經濟體港口停泊時間對比")
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

    st.write("---")

    # 📊 第二層：統計箱線圖 (Boxplot)
    st.header("📊 進階統計：船舶類型與核心指標分佈")
    tab1, tab2 = st.tabs(["⏳ 在港停泊時間分佈", "🚢 船舶平均總噸位分佈"])

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
        if 'avg_size_GT' in filtered_df.columns and filtered_df['avg_size_GT'].sum() > 0:
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
        else:
            st.info("ℹ️ 當前資料集未包含有效的總噸位 (GT) 數據欄位。")

    # 數據摘要查看
    with st.expander("🔍 查看目前篩選的原始資料摘要"):
        st.dataframe(filtered_df)
