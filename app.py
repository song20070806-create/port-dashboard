import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# 設定網頁標題與寬度
st.set_page_config(page_title="全球港口績效動態儀表板", layout="wide")

# ==============================================================================
# 🎯 核心功能：精準字串對齊與清洗邏輯（徹底修復欄位錯位與一條直線問題）
# ==============================================================================
@st.cache_data
def load_and_clean_data():
    file_name = "US_PortCalls_S.csv"
    df = pd.read_csv(file_name)
    
    # 清除欄位名稱前後可能多出來的隱形空格
    df.columns = df.columns.str.strip()
    
    # 建立一個新表格，直接用原始 CSV 裡面的精準英文名稱去抓取！
    new_df = pd.DataFrame()
    
    # 1. 精準對齊三大文字維度
    new_df['economy_label'] = df["Economy/Label"] if "Economy/Label" in df.columns else df.iloc[:, 0]
    new_df['vessel_type'] = df["Vessel type/Label"] if "Vessel type/Label" in df.columns else df.iloc[:, 1]
    new_df['period'] = df["Period/Label"] if "Period/Label" in df.columns else df.iloc[:, -1]
    
    # 2. 精準對齊六大數值指標
    # 針對原始 CSV 中帶有 "_Value" 的數值欄位進行精準提取
    num_mapping = {
        'avg_vessel_age': 'Average age of vessels_Value',
        'median_time_in_port': 'Median time spent in port (days)_Value',
        'avg_size_GT': 'Average size (GT) of vessels_Value',
        'avg_cargo_capacity_DWT': 'Average cargo carrying capacity (DWT) of vessels_Value',
        'max_size_GT': 'Maximum size (GT) of vessels_Value',
        'max_cargo_capacity_DWT': 'Maximum cargo carrying capacity (DWT) of vessels_Value'
    }
    
    for short_name, orig_name in num_mapping.items():
        if orig_name in df.columns:
            # 將 Kaggle 常見的文字髒資料替換成真正的空值，再強轉成數字
            s = df[orig_name].replace("Not available or not separately reported", pd.NA)
            new_df[short_name] = pd.to_numeric(s, errors='coerce')
        else:
            # 如果真的沒抓到該欄位，試著用位置推算，或者給空值
            new_df[short_name] = np.nan

    # 3. 填補中位數（完全還原 Kaggle 缺失值填補精髓）
    for col in num_mapping.keys():
        median_val = new_df[col].median()
        if pd.isna(median_val):
            median_val = 0.0
        new_df[col] = new_df[col].fillna(median_val)
        
    # 4. 文字標籤親民化美化
    new_df['economy_label'] = new_df['economy_label'].fillna("Unknown").astype(str).str.strip()
    new_df
