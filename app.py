import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# 1. 網頁基本組態設定
st.set_page_config(page_title="全球港口績效動態儀表板", layout="wide", page_icon="⚓️")

# 🌊 注入頂級海洋風（Deep Ocean）與「頂部密集泡泡 + 底部搖曳海草與小魚」特效
st.markdown("""
    <style>
        /* 網頁主背景：深海漸層色 */
        .stApp {
            background: linear-gradient(180deg, #050E1A 0%, #0B1E36 50%, #030812 100%) !important;
            color: #E2E8F0 !important;
            position: relative;
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

        /* 💦 頂部「多層次發光密集水花泡泡」區塊 */
        .ocean-splash-container {
            position: relative;
            width: 100%;
            height: 80px;
            overflow: hidden;
            margin-bottom: -30px;
        }
        .splash-bubble {
            position: absolute;
            background: linear-gradient(135deg, rgba(56, 189, 248, 0.35) 0%, rgba(14, 165, 233, 0.05) 100%);
            border: 1px solid rgba(255, 255, 255, 0.15);
            border-radius: 50%;
            box-shadow: 0 0 12px rgba(56, 189, 248, 0.25);
            animation: floatBubble 4s ease-in-out infinite alternate;
        }
        /* 增加到 10 個錯落有致的泡泡 */
        .b1 { width: 35px; height: 35px; top: 25px; left: 5%; animation-delay: 0s; animation-duration: 3.5s; }
        .b2 { width: 18px; height: 18px; top: 10px; left: 12%; animation-delay: 0.5s; animation-duration: 4.5s; }
        .b3 { width: 25px; height: 25px; top: 40px; left: 22%; animation-delay: 1.2s; animation-duration: 3s; }
        .b4 { width: 45px; height: 45px; top: -5px; left: 38%; animation-delay: 0.8s; animation-duration: 5s; }
        .b5 { width: 15px; height: 15px; top: 30px; left: 50%; animation-delay: 0.2s; animation-duration: 4s; }
        .b6 { width: 30px; height: 30px; top: 15px; left: 62%; animation-delay: 1.5s; animation-duration: 3.8s; }
        .b7 { width: 22px; height: 22px; top: 35px; left: 70%; animation-delay: 0.4s; animation-duration: 4.2s; }
        .b8 { width: 40px; height: 40px; top: 10px; left: 80%; animation-delay: 1.1s; animation-duration: 4.8s; }
        .b9 { width: 18px; height: 18px; top: 45px; left: 89%; animation-delay: 0.7s; animation-duration: 3.2s; }
        .b10 { width: 28px; height: 28px; top: 5px; left: 95%; animation-delay: 1.7s; animation-duration: 5.2s; }

        @keyframes floatBubble {
            0% { transform: translateY(0px) scale(0.95); opacity: 0.5; }
            100% { transform: translateY(-12px) scale(1.08); opacity: 0.85; }
        }

        /* 🌿 🐟 底部「搖曳海草與悠游小魚」生態區 */
        .sea-floor-aquarium {
            position: relative;
            width: 100%;
            height: 120px;
            background: linear-gradient(to top, rgba(3, 8, 18, 0.9) 0%, rgba(11, 30, 54, 0) 100%);
            margin-top: 40px;
            overflow: hidden;
            border-top: 1px solid rgba(56, 189, 248, 0.05);
        }
        
        /* 海草基本樣式與左右搖曳動畫 */
        .seaweed {
            position: absolute;
            bottom: 0;
            width: 8px;
            background: linear-gradient(to top, #064E3B 0%, #059669 70%, #34D399 100%);
            border-radius: 4px 4px 0 0;
            opacity: 0.7;
            transform-origin: bottom center;
            animation: sway 3s ease-in-out infinite alternate;
        }
        .sw1 { height: 75px; left: 4%; animation-duration: 2.8s; }
        .sw2 { height: 90px; left: 5%; animation-duration: 3.4s; animation-delay: 0.3s; }
        .sw3 { height: 60px; left: 6%; animation-duration: 2.5s; animation-delay: 0.6s; }
        
        .sw4 { height: 80px; left: 48%; animation-duration: 3.1s; }
        .sw5 { height: 100px; left: 49%; animation-duration: 3.6s; animation-delay: 0.4s; }
        
        .sw6 { height: 70px; left: 91%; animation-duration: 2.7s; }
        .sw7 { height: 95px; left: 92%; animation-duration: 3.3s; animation-delay: 0.2s; }
        .sw8 { height: 65px; left: 93%; animation-duration: 2.9s; animation-delay: 0.5s; }

        @keyframes sway {
            0% { transform: rotate(-5deg) skewX(-3deg); }
            100% { transform: rotate(5deg) skewX(3deg); }
        }

        /* 游動小魚樣式 */
        .aquarium-fish {
            position: absolute;
            font-size: 18px;
            opacity: 0.8;
            text-shadow: 0 0 8px rgba(56, 189, 248, 0.5);
            animation: swim 12s linear infinite;
        }
        .f1 { bottom: 45px; animation-duration: 14s; animation-delay: 0s; }
        .f2 { bottom: 20px; animation-duration: 18s; animation-delay: 4s; }
        .f3 { bottom: 70px; animation-duration: 11s; animation-delay: 2s; }

        @keyframes swim {
            0% { left: -5%; transform: scaleX(1); }
            49% { transform: scaleX(1); }
            50% { left: 105%; transform: scaleX(-1); } /* 到達右側後原地轉向 */
            99% { transform: scaleX(-1); }
            100% { left: -5%; transform: scaleX(1); } /* 游回左側 */
        }
        
        /* 側邊欄邊框 */
        [data-testid="stSidebar"] {
            background-color: #030A16 !important;
            border-right: 2px solid #0284C7 !important;
            box-shadow: 5px 0px 15px rgba(2, 132, 199, 0.1);
        }
        
        /* 標題發光效果 */
        h1, h2, h3 {
            color: #38BDF8 !important;
            font-family: 'Helvetica Neue', sans-serif;
            font-weight: 700 !important;
            text-shadow: 0px 0px 12px rgba(56, 189, 248, 0.4);
        }
        
        /* 表籤（Tabs）與摺疊面板 */
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
        
        /* 卡片懸浮特效 */
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
# 🌊 1. 頂部密集飛舞的「水花泡泡」群
st.markdown("""
    <div class="ocean-splash-container">
        <div class="splash-bubble b1"></div><div class="splash-bubble b2"></div>
        <div class="splash-bubble b3"></div><div class="splash-bubble b4"></div>
        <div class="splash-bubble b5"></div><div class="splash-bubble b6"></div>
        <div class="splash-bubble b7"></div><div class="splash-bubble b8"></div>
        <div class="splash-bubble b9"></div><div class="splash-bubble b10"></div>
    </div>
""", unsafe_allow_html=True)

# 頂部大標題
st.title("⚓️ 全球海事港口績效動態儀表板")
st.caption("🌊 *基於 UNCTAD 全球航運大數據，動態追蹤全球主要經濟體之港口週轉時效與運力分佈*")

if df_cleaned.empty:
    st.error("⚠️ 資料集清洗後為空。")
else:
    # 側邊欄航海控制中心
    st.sidebar.markdown("## ☸️ 航海控制中心")
    st.sidebar.write("---")

    selected_period = st.sidebar.selectbox("📅 選擇報告期間 (Period)", sorted(list(df_cleaned['period'].unique())), index=0)
    period_df = df_cleaned[df_cleaned['period'] == selected_period]

    all_vessels = sorted(list(period_df['vessel_type'].unique()))
    selected_vessels = st.sidebar.multiselect("🚢 選擇觀測船舶類型", all_vessels, default=all_vessels)
    max_countries = st.sidebar.slider("🗺️ 顯示觀測國家數量", min_value=5, max_value=30, value=12)

    filtered_df = period_df[period_df['vessel_type'].isin(selected_vessels)]
    if filtered_df.empty:
        filtered_df = period_df

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

    # 📊 第二層：進階統計箱線圖
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

    # 🌿 🐟 2. 網頁最底部的「搖曳海草與悠游小魚」生態水族箱
    st.markdown("""
        <div class="sea-floor-aquarium">
            <div class="seaweed sw1"></div>
            <div class="seaweed sw2"></div>
            <div class="seaweed sw3"></div>
            
            <div class="seaweed sw4"></div>
            <div class="seaweed sw5"></div>
            
            <div class="seaweed sw6"></div>
            <div class="seaweed sw7"></div>
            <div class="seaweed sw8"></div>
            
            <div class="aquarium-fish f1">🐟</div>
            <div class="aquarium-fish f2">🐠</div>
            <div class="aquarium-fish f3">🐡</div>
        </div>
    """, unsafe_allow_html=True)
