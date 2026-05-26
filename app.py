import streamlit as st
import pandas as pd
import plotly.express as px

# 設定網頁排版
st.set_page_config(page_title="全球港口績效儀表板", layout="wide")
st.title("🚢 全球港口績效與塞港監測互動儀表板")
st.subheader("專案實作：跨時期港口停泊時間對比")

# 讀取並清洗資料
@st.cache_data
def load_and_clean_data():
    # 讀取下載下來的 csv 檔案
    raw_df = pd.read_csv("US_PortCalls_S.csv", na_values=["Not available or not separately reported"])
    df_container = raw_df[raw_df['CommercialMarket Label'] == 'Container ships'].copy()
    df_container['Median time in port (days)'] = pd.to_numeric(df_container['Median time in port (days)'], errors='coerce')
    clean_df = df_container.dropna(subset=['Median time in port (days)', 'Period Label', 'Economy Label'])
    return clean_df

df = load_and_clean_data()

# 側邊欄篩選器
st.sidebar.header("📊 網頁控制面板")
all_economies = df['Economy Label'].unique().tolist()
selected_economies = st.sidebar.multiselect(
    "選擇想要對比的國家/地區：",
    options=all_economies,
    default=all_economies
)

# 動態過濾與畫圖
df_filtered = df[df['Economy Label'].isin(selected_economies)]
# 動態過濾與畫圖
df_filtered = df[df['Economy Label'].isin(selected_economies)]

fig = px.line(
    df_filtered, 
    x='Period Label', 
    y='Median time in port (days)', 
    color='Economy Label',
    markers=True,
    title="2018-2023 貨櫃船在港時間中位數（天）趨勢對比",
    labels={'Median time in port (days)': '在港時間 (天)', 'Period Label': '時間軸 (半年報)'}
)

# 修正後的正確排版寫法：把 tickangle 放進 xaxis 裡面
fig.update_layout(
    hovermode="x unified",
    xaxis=dict(tickangle=45)
)

st.plotly_chart(fig, use_container_width=True)
st.info("💡 互動提示：你可以用滑鼠游標移到圖表的線條上，會動態顯示精確的數值；也可以利用左側控制面板自由隱藏/顯示特定國家。")