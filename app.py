import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# 1. 網頁基本設定
st.set_page_config(page_title="全球港口績效動態儀表板", layout="wide")

# 2. 完全不使用任何 @st.cache_data 裝飾器，每次網頁重新整理就一定強制重新讀取檔案！
def load_data_force_refresh():
    file_name = "US_PortCalls_S.csv"
    try:
        # 使用 utf-8-sig 強制消除可能干擾的隱形編碼字元
        df = pd.read_csv(file_name, encoding='utf-8-sig')
    except Exception as e:
        st.error(f"❌ 無法讀取 CSV 檔案，請確認 {file_name} 是否與 app.py 在同一個 GitHub 資料夾內。錯誤: {e}")
        return pd.DataFrame()

    if df.empty:
        return pd.DataFrame()

    # 清理所有原始欄位名稱的隱形空格
    df.columns = df.columns.str.strip()
    
    # 建立一個乾淨的 DataFrame
    new_df = pd.DataFrame()
    
    # 採用最暴力的「名稱 + 位置」雙重保障抓取法
    try:
        # 國家/經濟體
        new_df['economy_label'] = df['Economy_Label'] if 'Economy_Label' in df.columns else df.iloc[:, 0]
        # 船舶類型
        new_df['vessel_type'] = df['CommercialMarket_Label'] if 'CommercialMarket_Label' in df.columns else df.iloc[:, 1]
        # 停泊中位數時間
        new_df['median_time_in_port'] = df['Median_time_in_port_days_Value'] if 'Median_time_in_port_days_Value' in df.columns else df.iloc[:, 5]
        # 船舶平均總噸位
        new_df['avg_size_GT'] = df['Average_size_GT_Value'] if 'Average_size_GT_Value' in df.columns else df.iloc[:, 7]
        # 報告期間
        new_df['period'] = df['period'] if 'period' in df.columns else df.iloc[:, -1]
    except Exception as e:
        st.error(f"❌ 擷取 CSV 欄位時發生錯誤: {e}")
        return pd.DataFrame()

    # 將所有欄位內容轉為標準字串並拔除前後空格、雙引號
    for col in new_df.columns:
        new_df[col] = new_df[col].astype(str).str.replace('"', '').str.strip()

    # 清洗掉資料裡面的標題列雜訊與 World 總計
    new_df = new_df[~new_df['period'].str.contains('period', case=False, na=False)]
    new_df = new_df[~new_df['economy_label'].str.contains('Economy|World', case=False, na=False)]

    # 安全數值轉換
    def clean_to_num(series):
        s = series.replace(["Not available or not separately reported", "nan", "NaN", "null", ""], np.nan)
        return pd.to_numeric(s, errors='coerce')

    new_df['median_time_in_port'] = clean_to_num(new_df['median_time_in_port'])
    new_df['avg_size_GT'] = clean_to_num(new_df['avg_size_GT'])

    # 只要時間不是空值的，我們就留下來
    new_df = new_df.dropna(subset=['median_time_in_port']).reset_index(drop=True)
    return new_df

# 執行讀取
df_cleaned = load_data_force_refresh()

# ==============================================================================
# 🎛️ 前端介面渲染
# ==============================================================================
st.title("⚓️ 全球海事港口績效動態儀表板")

if df_cleaned.empty:
    st.error("⚠️ 系統讀取到的資料為空。請確認您的 'US_PortCalls_S.csv' 檔案是否有成功上傳到 GitHub，且與 app.py 放再同一個目錄下。")
    
    # 現場就地除錯：如果找得到檔案，直接印出前幾行
    try:
        debug_df = pd.read_csv("US_PortCalls_S.csv", nrows=5)
        st.write("🔧 偵測到 CSV 檔案存在！以下為該檔案的原始前幾筆資料，供您核對：")
        st.dataframe(debug_df)
    except:
        st.warning("🔧 系統目前在您的 GitHub 目錄下『完全找不到』名為 US_PortCalls_S.csv 的檔案！")
else:
    st.sidebar.header("📊 數據篩選中心")

    # 1. 選擇期間
    all_periods = sorted(list(df_cleaned['period'].unique()))
    selected_period = st.sidebar.selectbox("選擇報告期間 (Period)", all_periods, index=0)
    
    # 切出該期間資料
    period_df = df_cleaned[df_cleaned['period'] == selected_period]

    # 2. 選擇船型
    all_vessels = sorted(list(period_df['vessel_type'].unique()))
    selected_vessels = st.sidebar.multiselect("選擇船舶類型", all_vessels, default=all_vessels)

    # 3. 顯示數量
    max_countries = st.sidebar.slider("顯示國家數量", min_value=5, max_value=40, value=15)

    # 最終過濾
    filtered_df = period_df[period_df['vessel_type'].isin(selected_vessels)]

    # 🔥 終極保底防禦：如果過濾完是空的，直接強行恢復成整個期間的資料，拒絕顯示空白畫面！
    if filtered_df.empty:
        filtered_df = period_df

    st.markdown(f"**當前分析期間： `{selected_period}`**")
    st.write("---")

    # 📊 各經濟體港口停泊時間對比
    st.header("📊 各經濟體港口停泊時間對比")
    plot_df = filtered_df.sort_values(by='median_time_in_port', ascending=False).head(max_countries)
    
    fig_bar = px.bar(
        plot_df,
        x='economy_label',
        y='median_time_in_port',
        color='vessel_type',
        barmode='group',
        title=f"各經濟體船舶在港中位數時間排行",
        labels={'economy_label': '經濟體/國家', 'median_time_in_port': '停泊中位數時間 (天)', 'vessel_type': '船舶類型'},
        template="plotly_dark",
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    fig_bar.update_layout(xaxis_tickangle=-45, height=550)
    st.plotly_chart(fig_bar, use_container_width=True)

    st.write("---")

    # 📊 進階統計箱線圖
    st.header("📊 進階統計：船舶類型與核心指標分佈 (Boxplot)")
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

    # 底部數據摘要展開檢查
    with st.expander("🔍 查看目前篩選的原始資料摘要"):
        st.dataframe(filtered_df)
