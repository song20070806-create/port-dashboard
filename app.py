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
        # 讀取資料
        df = pd.read_csv(file_name)
    except Exception as e:
        st.error(f"❌ 無法讀取 CSV 檔案：{e}")
        return pd.DataFrame()

    # 剔除未命名的流水號欄位
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    
    new_df = pd.DataFrame()
    
    # 根據你最新圖表對應的欄位位置與特徵進行安全擷取
    new_df['economy_label'] = df.iloc[:, 0].astype(str).str.replace('"', '').str.strip()
    
    # 船舶類型（在此資料集中為數值代號，我們保留它並轉為字串方便分類）
    new_df['vessel_type'] = df.iloc[:, 1].astype(str).str.replace('"', '').str.strip()
    
    # 時間報告期間
    if df.shape[1] >= 9:
        new_df['period'] = df.iloc[:, 8].astype(str).str.replace('"', '').str.strip()
    else:
        new_df['period'] = df.iloc[:, -1].astype(str).str.replace('"', '').str.strip()

    # 數值指標清洗（徹底拔除雙引號）
    def to_numeric_clean(series):
        s = series.astype(str).str.replace('"', '').str.strip()
        return pd.to_numeric(s, errors='coerce')

    new_df['median_time_in_port'] = to_numeric_clean(df.iloc[:, 2])
    new_df['avg_size_GT'] = to_numeric_clean(df.iloc[:, 3])

    # 移除標題列等雜訊
    new_df = new_df[~new_df['period'].str.contains('Period', case=False, na=False)]
    new_df = new_df[~new_df['economy_label'].str.contains('Economy', case=False, na=False)]
    
    # 剔除無效的空值，確保圖表有真實波動
    new_df = new_df.dropna(subset=['median_time_in_port']).reset_index(drop=True)
    
    return new_df

df_cleaned = load_and_clean_data()

# ==============================================================================
# 🎛️ 前端網頁渲染
# ==============================================================================
if df_cleaned.empty:
    st.error("⚠️ 資料集清洗後為空，請檢查 CSV 檔案內容。")
else:
    st.sidebar.header("📊 數據篩選中心")

    # 1. 期間篩選（這步至關重要！選定單一時間才不會讓線連成毛線球）
    all_periods = sorted(list(df_cleaned['period'].unique()))
    selected_period = st.sidebar.selectbox("選擇報告期間 (Period)", all_periods, index=len(all_periods)-1 if all_periods else 0)

    # 2. 船舶類型（數字代號）篩選器
    all_vessels = sorted(list(df_cleaned['vessel_type'].unique()))
    selected_vessels = st.sidebar.multiselect("選擇船舶類型代號", all_vessels, default=all_vessels[:3] if len(all_vessels) >= 3 else all_vessels)

    # 3. 限制顯示國家數
    max_countries = st.sidebar.slider("顯示國家數量", min_value=5, max_value=30, value=15)

    # 動態過濾
    filtered_df = df_cleaned[
        (df_cleaned['period'] == selected_period) & 
        (df_cleaned['vessel_type'].isin(selected_vessels))
    ]

    st.title("⚓️ 全球海事港口績效動態儀表板")
    st.markdown(f"**當前分析期間： `{selected_period}`** | 船舶類型已識別為分類代碼。")
    st.write("---")

    # 💡 修正後的主圖表：使用長條圖 (Bar Chart) 完美取代死板連線的折線圖！
    st.header("📊 各經濟體港口停泊時間對比 (長條圖)")
    
    plot_df = filtered_df.sort_values(by='median_time_in_port', ascending=False).head(max_countries)
    
    if not plot_df.empty:
        # 用 barmode="group" 讓不同船型在同一個國家下並排顯示，再也不會亂連線！
        fig_bar = px.bar(
            plot_df,
            x='economy_label',
            y='median_time_in_port',
            color='vessel_type',
            barmode='group',
            title=f"各經濟體船舶在港中位數時間 (期間: {selected_period})",
            labels={'economy_label': '經濟體/國家', 'median_time_in_port': '停泊中位數時間 (天)', 'vessel_type': '船舶類型代號'},
            template="plotly_dark"
        )
        fig_bar.update_layout(xaxis_tickangle=-45, height=550)
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.warning("⚠️ 當前篩選條件下無資料，請調整左側篩選器。")

    st.write("---")

    # 💡 第二層：散佈圖 (Scatter Plot) 查看分佈
    st.header("🔍 進階分析：港口停泊時間 vs 船舶總噸位")
    if not filtered_df.empty:
        fig_scatter = px.scatter(
            filtered_df,
            x='avg_size_GT',
            y='median_time_in_port',
            color='vessel_type',
            hover_data=['economy_label'],
            title="船舶噸位大小與停泊時間之關聯散佈圖",
            labels={'avg_size_GT': '平均總噸位 (GT)', 'median_time_in_port': '在港時間 (天)', 'vessel_type': '船舶代號'},
            template="plotly_dark"
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

    # 底部數據摘要檢查
    with st.expander("🔍 查看目前篩選的原始資料摘要"):
        st.dataframe(filtered_df)
