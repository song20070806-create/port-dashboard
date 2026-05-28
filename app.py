import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# 1. 網頁基本組態設定
st.set_page_config(page_title="全球港口績效動態儀表板", layout="wide")

# 🚢 船舶代號與中英文名稱的完整對照表（解決真實資料為數字代號的問題）
VESSEL_MAPPING = {
    '1.0': 'All ships (所有船型)',
    '1': 'All ships (所有船型)',
    '2.0': 'Liquid bulk carriers (液體散貨船)',
    '2': 'Liquid bulk carriers (液體散貨船)',
    '4.0': 'Dry bulk carriers (乾散貨船)',
    '4': 'Dry bulk carriers (乾散貨船)',
    '5.0': 'Dry breakbulk carriers (件雜貨船)',
    '5': 'Dry breakbulk carriers (件雜貨船)',
    '7.0': 'Liquefied petroleum gas carriers (液化石油氣船)',
    '7': 'Liquefied petroleum gas carriers (液化石油氣船)',
    '8.0': 'Liquefied natural gas carriers (液化天然氣船)',
    '8': 'Liquefied natural gas carriers (液化天然氣船)',
    '11.0': 'Container ships (貨櫃船)',
    '11': 'Container ships (貨櫃船)',
    '12.0': 'Passenger ships (客船)',
    '12': 'Passenger ships (客船)',
    '13.0': 'Roll-on/roll-off ships (滾裝船)',
    '13': 'Roll-on/roll-off ships (滾裝船)'
}

def load_and_clean_real_data():
    file_name = "US_PortCalls_S.csv"
    try:
        # 讀取 CSV，採用 utf-8-sig 防止看不見的編碼干擾
        df = pd.read_csv(file_name, encoding='utf-8-sig')
    except Exception as e:
        st.error(f"❌ 無法讀取 CSV 檔案：{e}")
        return pd.DataFrame()

    if df.empty:
        return pd.DataFrame()

    # 拔除所有原始欄位名稱的前後空格（修正 CSV 的欄位空格陷阱）
    df.columns = df.columns.str.strip()
    
    new_df = pd.DataFrame()
    
    try:
        # 對應真實 CSV 欄位名稱進行精準抓取
        new_df['period'] = df['Period'].astype(str).str.strip()
        new_df['period_label'] = df['Period Label'].astype(str).str.strip()
        new_df['economy_label'] = df['Economy Label'].astype(str).str.strip()
        
        # 讀取原始的船舶代號（去掉小數點與空白）
        raw_vessel = df['CommercialMarket Label'].astype(str).str.strip()
        
        # 核心修復：將數字代號對照轉換為漂亮的人類文字
        new_df['vessel_type'] = raw_vessel.map(VESSEL_MAPPING).fillna(raw_vessel)
        
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

    # 🛑 核心過濾：剔除標題雜訊，並刪除「World」與「Economy」等總計行（確保只留個別國家數據）
    new_df = new_df[~new_df['period'].str.contains('period', case=False, na=False)]
    new_df = new_df[~new_df['economy_label'].str.contains('World|Economy', case=False, na=False)]
    
    # 移除時間為空值的無效列
    new_df = new_df.dropna(subset=['median_time_in_port']).reset_index(drop=True)
    
    return new_df

# 強制不進行快取，每次重新整理都重新整理資料
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
    
    # 切出該期間的資料
    period_df = df_cleaned[df_cleaned['period'] == selected_period]

    # 2. 選擇船舶類型
    all_vessels = sorted(list(period_df['vessel_type'].unique()))
    
    # 預設幫使用者勾選前 5 個熱門船型（包含貨櫃船、散貨船等，避免畫面空白）
    default_selection = all_vessels[:5] if len(all_vessels) >= 5 else all_vessels
    selected_vessels = st.sidebar.multiselect("選擇船舶類型", all_vessels, default=default_selection)

    # 3. 顯示國家數量排行滑桿
    max_countries = st.sidebar.slider("顯示國家數量 (依國家平均停泊時間排行)", min_value=5, max_value=30, value=12)

    # 根據使用者勾選的船型進行最終資料過濾
    filtered_df = period_df[period_df['vessel_type'].isin(selected_vessels)]

    # 防止使用者不小心把船型全叉掉導致畫面壞掉的保底機制
    if filtered_df.empty:
        filtered_df = period_df

    st.markdown(f"**當前分析期間： `{selected_period}`**")
    st.write("---")

    # 📊 第一層：各經濟體港口停泊時間對比
    st.header("📊 各經濟體港口停泊時間對比")
    
    # 🎯 核心演算法修復：
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
    
    # 將數據依據各國平均時間重新排列，讓 X 軸從大到小視覺效果更完美
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
    
    # 🎯 安全修復：關掉滑鼠指過去時擾人的藍色水平對齊虛線 (Spikelines) 且保證絕不噴錯
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

    # 底部摺疊面板：供使用者快速核對原始數據
    with st.expander("🔍 查看目前篩選的原始資料摘要"):
        st.dataframe(filtered_df)
