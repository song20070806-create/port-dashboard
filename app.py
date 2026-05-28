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
        # 使用 utf-8-sig 讀取，自動消滅可能存在的隱形 BOM 碼
        df = pd.read_csv(file_name, encoding='utf-8-sig')
    except Exception as e:
        st.error(f"❌ 無法讀取 CSV 檔案：{e}")
        return pd.DataFrame()

    if df.empty:
        return pd.DataFrame()

    new_df = pd.DataFrame()
    
    # 🔥 終極大絕招：完全不用欄位名稱，直接用「欄位位置 (iloc)」強行抓取！
    # 這樣管他 CSV 裡面欄位叫什麼名字、有沒有空格，都不可能噴 KeyError 報錯。
    try:
        # 第 1 欄 (Index 0): 國家
        new_df['economy_label'] = df.iloc[:, 0].astype(str).str.replace('"', '').str.strip()
        
        # 第 2 欄 (Index 1): 船舶類型文字
        new_df['vessel_type'] = df.iloc[:, 1].astype(str).str.replace('"', '').str.strip()
        
        # 第 6 欄 (Index 5): 港口停泊時間中位數
        new_df['median_time_in_port'] = df.iloc[:, 5].astype(str).str.replace('"', '').str.strip()
        
        # 第 8 欄 (Index 7): 船舶平均總噸位
        new_df['avg_size_GT'] = df.iloc[:, 7].astype(str).str.replace('"', '').str.strip()
        
        # 最後一欄 (Index -1): 期間 period
        new_df['period'] = df.iloc[:, -1].astype(str).str.replace('"', '').str.strip()
    except Exception as e:
        st.error(f"❌ 擷取欄位位置時出錯，請確認 CSV 欄位數量是否足夠：{e}")
        return pd.DataFrame()

    # 安全轉換數值函數
    def to_numeric_clean(series):
        s = series.replace(["Not available or not separately reported", "nan", "NaN", "null", ""], np.nan)
        return pd.to_numeric(s, errors='coerce')

    new_df['median_time_in_port'] = to_numeric_clean(new_df['median_time_in_port'])
    new_df['avg_size_GT'] = to_numeric_clean(new_df['avg_size_GT'])

    # 資料過濾：移除重複的標題列雜訊、空白值與 World 總計
    new_df = new_df[~new_df['period'].str.contains('period', case=False, na=False)]
    new_df = new_df[~new_df['economy_label'].str.contains('Economy|World', case=False, na=False)]
    
    # 剔除停泊時間為空值的資料
    new_df = new_df.dropna(subset=['median_time_in_port']).reset_index(drop=True)
    
    return new_df

df_cleaned = load_and_clean_data()

# ==============================================================================
# 🎛️ 前端網頁渲染
# ==============================================================================
if df_cleaned.empty:
    st.error("⚠️ 資料集清洗後為空。請確保 CSV 檔案與 app.py 放再同一個資料夾。")
else:
    st.sidebar.header("📊 數據篩選中心")

    # 1. 期間篩選器
    all_periods = sorted(list(df_cleaned['period'].unique()))
    selected_period = st.sidebar.selectbox("選擇報告期間 (Period)", all_periods, index=0)

    period_df = df_cleaned[df_cleaned['period'] == selected_period]

    # 2. 船舶類型篩選器（預設直接全選，確保一定看得到圖表）
    all_vessels = sorted(list(period_df['vessel_type'].unique()))
    selected_vessels = st.sidebar.multiselect("選擇船舶類型", all_vessels, default=all_vessels)

    # 3. 限制顯示國家數
    max_countries = st.sidebar.slider("顯示國家數量 (依停泊時間排行)", min_value=5, max_value=40, value=15)

    # 最終過濾資料
    filtered_df = period_df[period_df['vessel_type'].isin(selected_vessels)]

    # --- 主網頁畫面 ---
    st.title("⚓️ 全球海事港口績效動態儀表板")
    st.markdown(f"**當前分析期間： `{selected_period}`**")
    st.write("---")

    # 💡 第一層：美化版分組長條圖
    st.header("📊 各經濟體港口停泊時間對比")
    
    if not filtered_df.empty:
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
    else:
        st.warning("⚠️ 當前篩選條件下無資料，請在左側側邊欄重新勾選船舶類型。")

    st.write("---")

    # 💡 第二層：雙指標統計箱線圖
    st.header("📊 進階統計：船舶類型與核心指標分佈 (Boxplot)")
    
    if not filtered_df.empty:
        tab1, tab2 = st.tabs(["⏳ 在港停泊時間分佈", "🚢 船舶平均總噸位 (GT) 分佈"])

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

    # 底部數據摘要檢查
    with st.expander("🔍 查看目前篩選的原始資料摘要"):
        st.dataframe(filtered_df)
