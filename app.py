import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# 1. 網頁基本組態設定
st.set_page_config(page_title="全球港口績效動態儀表板", layout="wide", page_icon="⚓️")

# 🌊 注入頂級海洋風（Deep Ocean）與頂部「海浪水花」動態視覺點綴
st.markdown("""
    <style>
        /* 網頁主背景：深海漸層色 */
        .stApp {
            background: linear-gradient(180deg, #061124 0%, #0B1E36 50%, #050C1A 100%) !important;
            color: #E2E8F0 !important;
        }

        /* 🌊 網頁最頂部「海浪波紋」裝飾條 */
        .stApp::before {
            content: "";
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 12px;
            background: linear-gradient(90deg, #0284C7 0%, #38BDF8 50%, #0D9488 100%);
            box-shadow: 0px 3px 20px rgba(56, 189, 248, 0.6);
            z-index: 999;
        }

        /* 💦 自訂頂部「發光水花泡泡」特效區塊 */
        .ocean-splash-container {
            position: relative;
            width: 100%;
            height: 60px;
            overflow: hidden;
            margin-bottom: -20px;
        }
        .splash-bubble {
            position: absolute;
            background: linear-gradient(135deg, rgba(56, 189, 248, 0.4) 0%, rgba(14, 165, 233, 0.1) 100%);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 50%;
            box-shadow: 0 0 15px rgba(56, 189, 248, 0.3);
            animation: floatBubble 4s ease-in-out infinite alternate;
        }
        /* 設定不同大小位置的水花，製造錯落感 */
        .b1 { width: 35px; height: 35px; top: 15px; left: 8%; animation-delay: 0s; }
        .b2 { width: 20px; height: 20px; top: 5px; left: 15%; animation-delay: 0.5s; }
        .b3 { width: 45px; height: 45px; top: -10px; left: 45%; animation-delay: 1s; }
        .b4 { width: 25px; height: 25px; top: 20px; left: 75%; animation-delay: 0.2s; }
        .b5 { width: 30px; height: 30px; top: 8px; left: 88%; animation-delay: 1.5s; }

        @keyframes floatBubble {
            0% { transform: translateY(0px) scale(1); opacity: 0.6; }
            100% { transform: translateY(-8px) scale(1.08); opacity: 0.9; }
        }
        
        /* 側邊欄：深海藍加上「極光發光海岸線」邊框 */
        [data-testid="stSidebar"] {
            background-color: #030A16 !important;
            border-right: 2px solid #0284C7 !important;
            box-shadow: 5px 0px 15px rgba(2, 132, 199, 0.1);
        }
        
        /* 標題與副標題：水藍色發光特效 */
        h1, h2, h3 {
            color: #38BDF8 !important;
            font-family: 'Helvetica Neue', sans-serif;
            font-weight: 700 !important;
            text-shadow: 0px 0px 12px rgba(56, 189, 248, 0.4);
            letter-spacing: 0.5px;
        }
        
        /* 表籤（Tabs）與摺疊面板樣式優化 */
        .stTabs [data-baseweb="tab-list"] {
            background-color: rgba(11, 30, 54, 0.7);
            border-radius: 10px;
            padding: 4px;
            border: 1px solid rgba(56, 189, 248, 0.2);
        }
        .stTabs [data-baseweb="tab"] {
            color: #94A3B8 !important;
            border-radius: 6px;
        }
        .stTabs [aria-selected="true"] {
            background-color: #0284C7 !important;
            color: #FFFFFF !important;
            font-weight: bold !important;
        }
        
        /* 懸浮卡片特效 */
        div.stBlock {
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        div.stBlock:hover {
            transform: translateY(-2px);
            box-shadow: 0px 8px 20px rgba(56, 189, 248, 0.1);
        }

        p, span, label {
            color: #A5F3FC !important;
        }
    </style>
""", unsafe_allow_html=True)

# 🌍 國家/經濟體中文化對照表
COUNTRY_MAPPING = {
    'Philippines': '菲律賓 (Philippines)',
    'Türkiye': '土耳其 (Türkiye)',
    'Italy': '義大利 (Italy)',
    'Indonesia': '印尼 (Indonesia)',
    'France': '法國 (France)',
    'United Kingdom': '英國 (United Kingdom)',
    'Russian Federation': '俄羅斯 (Russian Federation)',
    'Korea, Republic of': '南韓 (South Korea)',
    'China': '中國 (China)',
    'Croatia': '克羅埃西亞 (Croatia)',
    'Australia': '澳洲 (Australia)',
    'United States of America': '美國 (United States)',
    'Germany': '德國 (Germany)',
    'Spain': '西班牙 (Spain)',
    'Japan': '日本 (Japan)',
    'Singapore': '新加坡 (Singapore)',
    'Malaysia': '馬來西亞 (Malaysia)',
    'Viet Nam': '越南 (Vietnam)',
    'Thailand': '泰國 (Thailand)',
    'India': '印度 (India)',
    'Brazil': '巴西 (Brazil)',
    'Canada': '加拿大 (Canada)',
    'Netherlands': '荷蘭 (Netherlands)',
    'Belgium': '比利時 (Belgium)'
}

# 🚢 船舶類型中文化對照
VESSEL_ZH_MAPPING = {
    'All ships': '所有船型 (All ships)',
    'Liquid bulk carriers': '液體散貨船 (Liquid bulk)',
    'Dry bulk carriers': '乾散貨船 (Dry bulk)',
    'Dry breakbulk carriers': '件雜貨船 (Dry breakbulk)',
    'Liquefied petroleum gas carriers': '液化石油氣船 (LPG)',
    'Liquefied natural gas carriers': '液化天然氣船 (LNG)',
    'Container ships': '貨櫃船 (Container)',
    'Passenger ships': '客船 (Passenger)',
    'Roll-on/roll-off ships': '滾裝船 (Ro-Ro)'
}

# 🎨 終極顏色綁定字典
COLOR_MAP = {
    '所有船型 (All ships)': '#7DD3FC',               
    '液體散貨船 (Liquid bulk)': '#FCD34D',              
    '乾散貨船 (Dry bulk)': '#38BDF8',                 
    '件雜貨船 (Dry breakbulk)': '#FB923C',            
    '液化石油氣船 (LPG)': '#F472B6',                  
    '液化天然氣船 (LNG)': '#C084FC',                  
    '貨櫃船 (Container)': '#6EE7B7',                 
    '客船 (Passenger)': '#94A3B8',                  
    '滾裝船 (Ro-Ro)': '#FCA5A5'                      
}

def load_and_clean_real_data():
    file_name = "US_PortCalls_S.csv"
    try:
        df = pd.read_csv(file_name, encoding='utf-8-sig')
    except Exception as e:
        st.error(f"❌ 無法讀取 CSV 檔案：{e}")
        return pd.DataFrame()

    if df.empty:
        return pd.DataFrame()

    df.columns = df.columns.str.strip()
    new_df = pd.DataFrame()
    
    try:
        new_df['period'] = df['Period'].astype(str).str.strip()
        new_df['period_label'] = df['Period Label'].astype(str).str.strip()
        
        raw_economy = df['Economy Label'].astype(str).str.strip()
        raw_vessel = df['CommercialMarket Label'].astype(str).str.strip()
        
        new_df['economy_label'] = raw_economy.map(COUNTRY_MAPPING).fillna(raw_economy)
        new_df['vessel_type'] = raw_vessel.map(VESSEL_ZH_MAPPING).fillna(raw_vessel)
        
        s_time = df['Median time in port (days)'].astype(str).str.replace('"', '').str.strip()
        s_time = s_time.replace(["Not available or not separately reported", "nan", "NaN", "null", ""], np.nan)
        new_df['median_time_in_port'] = pd.to_numeric(s_time, errors='coerce')
        
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

    new_df = new_df[~new_df['period'].str.contains('period', case=False, na=False)]
    new_df = new_df[~new_df['economy_label'].str.contains('World|total|economies', case=False, na=False)]
    new_df = new_df.dropna(subset=['median_time_in_port']).reset_index(drop=True)
    
    return new_df

df_cleaned = load_and_clean_real_data()

# ==============================================================================
# 🎛️ 前端網頁介面渲染
# ==============================================================================
# 🌊 在標題最上方渲染出自訂的「海浪水花泡泡」區塊
st.markdown("""
    <div class="ocean-splash-container">
        <div class="splash-bubble b1"></div>
        <div class="splash-bubble b2"></div>
        <div class="splash-bubble b3"></div>
        <div class="splash-bubble b4"></div>
        <div class="splash-bubble b5"></div>
    </div>
""", unsafe_allow_html=True)

# 頂部海洋風標題
st.title("⚓️ 全球海事港口績效動態儀表板")
st.caption("🌊 *基於 UNCTAD 全球航運大數據，動態追蹤全球主要經濟體之港口週轉時效與運力分佈*")

if df_cleaned.empty:
    st.error("⚠️ 資料集清洗後為空。")
else:
    # 側邊欄點綴
    st.sidebar.markdown("## ☸️ 航海控制中心")
    st.sidebar.write("---")

    # 1. 選擇報告期間
    selected_period = st.sidebar.selectbox("📅 選擇報告期間 (Period)", sorted(list(df_cleaned['period'].unique())), index=0)
    
    period_df = df_cleaned[df_cleaned['period'] == selected_period]

    # 2. 選擇船舶類型
    all_vessels = sorted(list(period_df['vessel_type'].unique()))
    selected_vessels = st.sidebar.multiselect("🚢 選擇觀測船舶類型", all_vessels, default=all_vessels)

    # 3. 顯示國家數量排行滑桿
    max_countries = st.sidebar.slider("🗺️ 顯示觀測國家數量", min_value=5, max_value=30, value=12)

    # 數據篩選
    filtered_df = period_df[filtered_df['vessel_type'].isin(selected_vessels)] if 'filtered_df' in locals() else period_df[period_df['vessel_type'].isin(selected_vessels)]
    if filtered_df.empty:
        filtered_df = period_df

    # 中央主面板點綴
    col_info1, col_info2 = st.columns(2)
    with col_info1:
        st.markdown(f"🚩 **當前航行航期：** `{selected_period}`")
    with col_info2:
        st.markdown(f"🔮 **當前監測船群：** 已鎖定 `{len(selected_vessels)}` 種核心船型")
    st.write("---")

    # 📊 第一層：長條圖
    st.header("📊 各經濟體港口停泊時間對比")
    
    top_countries = (
        filtered_df.groupby('economy_label')['median_time_in_port']
        .mean()
        .sort_values(ascending=False)
        .head(max_countries)
        .index.tolist()
    )
    
    plot_df = filtered_df[filtered_df['economy_label'].isin(top_countries)]
    plot_df = plot_df.sort_values(by='median_time_in_port', ascending=False)
    
    fig_bar = px.bar(
        plot_df,
        x='economy_label',
        y='median_time_in_port',
        color='vessel_type',
        barmode='group',
        title=f"各經濟體船舶在港中位數時間排行 (半年度航期: {selected_period})",
        labels={'economy_label': '經濟體 / 觀測國家', 'median_time_in_port': '停泊中位數時間 (天)', 'vessel_type': '船舶類型'},
        color_discrete_map=COLOR_MAP
    )
    
    fig_bar.update_layout(
        paper_bgcolor='rgba(0,0,0,0)', 
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#E2E8F0'),
        xaxis=dict(showspikes=False, tickangle=-45, gridcolor='rgba(255,255,255,0.02)'),
        yaxis=dict(showspikes=False, gridcolor='rgba(56, 189, 248, 0.1)'), 
        height=550
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    st.write("---")

    # 📊 第二層：進階統計箱線圖 (Boxplot)
    st.header("🔬 航運大數據分佈：船舶類型與核心指標")
    
    tab1, tab2 = st.tabs(["⏳ 船舶在港停泊天數分佈 (Days)", "🚢 航行船舶平均總噸位分佈 (GT)"])

    with tab1:
        fig_box1 = px.box(
            filtered_df,
            x='vessel_type',
            y='median_time_in_port',
            color='vessel_type',
            title="不同船舶類型的港口停泊時間機率分佈情況",
            labels={'vessel_type': '船舶類型', 'median_time_in_port': '在港時間 (天)'},
            points="all",
            color_discrete_map=COLOR_MAP
        )
        fig_box1.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#E2E8F0'),
            xaxis=dict(gridcolor='rgba(255,255,255,0.02)'),
            yaxis=dict(gridcolor='rgba(56, 189, 248, 0.1)'),
            height=500, 
            showlegend=False
        )
        st.plotly_chart(fig_box1, use_container_width=True)

    with tab2:
        if 'avg_size_GT' in filtered_df.columns and filtered_df['avg_size_GT'].sum() > 0:
            fig_box2 = px.box(
                filtered_df,
                x='vessel_type',
                y='avg_size_GT',
                color='vessel_type',
                title="不同船舶類型的平均總噸位大小 (GT) 分佈情況",
                labels={'vessel_type': '船舶類型', 'avg_size_GT': '平均總噸位 (GT)'},
                points="all",
                color_discrete_map=COLOR_MAP
            )
            fig_box2.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#E2E8F0'),
                xaxis=dict(gridcolor='rgba(255,255,255,0.02)'),
                yaxis=dict(gridcolor='rgba(56, 189, 248, 0.1)'),
                height=500, 
                showlegend=False
            )
            st.plotly_chart(fig_box2, use_container_width=True)
        else:
            st.info("ℹ️ 當前資料集未包含有效的總噸位數據。")

    # 原始資料摘要
    with st.expander("🔍 查看目前篩選的原始資料摘要"):
        st.dataframe(filtered_df)
