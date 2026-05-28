import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# 1. 網頁基本組態設定
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

    # 拔除所有原始欄位名稱的前後空格
    df.columns = df.columns.str.strip()
    
    new_df = pd.DataFrame()
    
    try:
        # 直接抓取最精準的欄位，不再需要代號轉換字典了！
        new_df['period'] = df['Period'].astype(str).str.strip()
        new_df['period_label'] = df['Period Label'].astype(str).str.strip()
        new_df['economy_label'] = df['Economy Label'].astype(str).str.strip()
        new_df['vessel_type'] = df['CommercialMarket Label'].astype(str).str.strip()
        
        # 安全清洗並轉換「港口停泊時間」為數值型態
        s_time = df['Median time in port (days)'].astype(str).str.replace('"', '').str.strip()
        s_time = s_time.replace(["Not available or not separately reported", "nan", "NaN", "null", ""], np.nan)
        new_df['median_time_in_port'] = pd.to_numeric(s_time, errors='coerce')
        
        # 安全清洗並轉換「船舶平均總噸位 (GT)」
        gt_cols = [c for c in df.columns if "size" in c.lower() or "gt" in c.lower()]
        if gt_cols:
            s_gt = df[gt_cols[0]].astype(str).str.replace('"', '').str.strip()
            s_gt = s_gt.replace(["Not available or not separately reported", "nan", "NaN", "null", ""], np.nan)
            new_df['avg_size_GT'] = pd.to_numeric(s_gt, errors='coerce')
        else:
            new_df['avg_size_GT'] = 0
            
    except Exception as e:
        st.error(f"❌ 欄位解析與清洗失敗: {e}")
        return pd.DataFrame()

    # 🛑 修正後的精準過濾：只剔除標題列本身，以及總計項目 "World"
    # 這樣絕對不會誤傷包含 "carriers" 或其他英文字的正常船型資料！
    new_df = new_df[~new_df['period'].str.contains('period', case=False, na=False)]
    new_df = new_df[new_df['economy_label'] != 'World']
    new_df = new_df[~new_df['economy_label'].str.contains('total|economies', case=False, na=False)]
    
    # 移除時間為空值的無效列
    new_df = new_df.dropna(subset=['median_time_in_port']).reset_index(drop=True)
    
    return new_df

df_cleaned = load_and_clean_real_data()

# ==============================================================================
# 🎛️ 前端網頁介面渲染
# ==============================================================================
st.title("⚓️ 全球海事港口績效動態儀表板")

if df_cleaned.empty:
    st.error("⚠️ 資料集清洗後為空，請確認您的 CSV 是否有成功上傳且格式正確。")
else:
    st.sidebar.header("📊 數據篩選中心")

    # 1. 選擇報告期間
    all_periods = sorted(list(df_cleaned['period'].unique()))
    selected_period = st.sidebar.selectbox("選擇報告期間 (Period)", all_periods, index=0)
    
    period_df = df_cleaned[df_cleaned['period'] == selected_period]

    # 2. 選擇船舶類型
    all_vessels = sorted(list(period_df['vessel_type'].unique()))
    
    # 預設直接幫使用者勾選「所有看得到的船型」，讓 Liquid bulk carriers 第一時間秀出來！
    selected_vessels = st.sidebar.multiselect("選擇船舶類型", all_vessels, default=all_vessels)

    # 3. 顯示國家數量排行滑桿
    max_countries = st.sidebar.slider("顯示國家數量 (依國家平均停泊時間排行)", min_value=5, max_value=30, value=12)

    # 根據使用者勾選的船型進行最終資料過濾
    filtered_df = period_df[period_df['vessel_type'].isin(selected_vessels)]

    if filtered_df.empty:
        filtered_df = period_df

    st.markdown(f"**當前分析期間： `{selected_period}`**")
    st.write("---")

    # 📊 各經濟體港口停泊時間對比
    st.header("📊 各經濟體港口停泊時間對比")
    
    # 先算出每個國家的平均在港停泊時間，並篩選出前 N 名的國家
    top_countries = (
        filtered_df.groupby('economy_label')['median_time_in_port']
        .mean()
        .sort_values(ascending=False)
        .head(max_countries)
        .index.tolist()
    )
    
    # 重新撈取這前 N 名國家中，所包含的所有勾選船型資料
    plot_df = filtered_df[filtered_df['economy_label'].isin(top_countries)]
    plot_df = plot_df.sort_values(by='median_time_in_port', ascending=False)
    
    # 繪製各國分組長條圖
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
    
    fig_bar.update_layout(
        xaxis=dict(showspikes=False),
        yaxis=dict(showspikes=False),
        xaxis_tickangle=-45,
        height=550
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    st.write("---")

    # 📊 第二層：進階統計箱線圖 (Boxplot)
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
            st.info("ℹ️ 當前資料集未包含有效的總噸位數據。")

    with st.expander("🔍 查看目前篩選的原始資料摘要"):
        st.dataframe(filtered_df)
