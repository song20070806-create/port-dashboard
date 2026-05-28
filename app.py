import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# 設定網頁標題與寬度
st.set_page_config(page_title="全球港口績效動態儀表板", layout="wide")

# ==============================================================================
# 🎯 核心功能：地毯式特徵強行對齊法（徹底根除 KeyError: 'period'）
# ==============================================================================
@st.cache_data
def load_and_clean_data():
    file_name = "US_PortCalls_S.csv"
    try:
        df = pd.read_csv(file_name)
    except Exception as e:
        st.error(f"❌ 無法讀取 CSV 檔案：{e}")
        return pd.DataFrame()

    # 剃除未命名的流水號欄位
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    
    # 建立全新的 DataFrame，這三個欄位名字一定要寫死，後面才不會 KeyError
    new_df = pd.DataFrame(columns=['economy_label', 'vessel_type', 'period'])
    
    # 1. 地毯式搜索時間欄位 (Period)
    found_period = False
    for col in df.columns:
        if "period" in col.lower() or "year" in col.lower() or "time/label" in col.lower():
            new_df['period'] = df[col].astype(str).str.strip()
            found_period = True
            break
    if not found_period: # 保底：如果都找不到，強行拿第 9 欄（索引 8）
        new_df['period'] = df.iloc[:, 8].astype(str).str.strip() if df.shape[1] >= 9 else df.iloc[:, -1].astype(str).str.strip()

    # 2. 地毯式搜索船舶類型 (Vessel Type)
    found_vessel = False
    for col in df.columns:
        if "vessel" in col.lower() or "ship" in col.lower():
            new_df['vessel_type'] = df[col].astype(str).str.strip()
            found_vessel = True
            break
    if not found_vessel: # 保底：拿第 2 欄
        new_df['vessel_type'] = df.iloc[:, 1].astype(str).str.strip()

    # 3. 地毯式搜索國家欄位 (Economy)
    found_economy = False
    for col in df.columns:
        if "economy" in col.lower() or "country" in col.lower() or "label" in col.lower() and col != df.columns[1]:
            new_df['economy_label'] = df[col].astype(str).str.strip()
            found_economy = True
            break
    if not found_economy: # 保底：拿第 1 欄
        new_df['economy_label'] = df.iloc[:, 0].astype(str).str.strip()

    # 4. 強行對齊並抓取六大核心數值
    target_numeric_names = [
        'avg_vessel_age', 'median_time_in_port', 'avg_size_GT', 
        'avg_cargo_capacity_DWT', 'max_size_GT', 'max_cargo_capacity_DWT'
    ]
    
    for i, target_name in enumerate(target_numeric_names):
        col_idx = 2 + i  # 從數值列起始位置開始抓
        if col_idx < df.shape[1]:
            s = df.iloc[:, col_idx].astype(str).replace("Not available or not separately reported", pd.NA)
            new_df[target_name] = pd.to_numeric(s, errors='coerce')
        else:
            new_df[target_name] = np.nan

    # 5. 數值缺失值中位數填補（對齊 Kaggle 精神）
    for col in target_numeric_names:
        median_val = new_df[col].median()
        if pd.isna(median_val):
            median_val = 0.0
        new_df[col] = new_df[col].fillna(median_val)
        
    # 文字標籤美化
    new_df['vessel_type'] = new_df['vessel_type'].replace({'All ships': 'All_Vessel_Types'})
    
    # 徹底清除第一列標題行可能帶進來的髒資料
    new_df = new_df[~new_df['period'].str.contains('Period', case=False, na=False)]
    new_df = new_df[~new_df['economy_label'].str.contains('Economy', case=False, na=False)]
    
    return new_df

df_cleaned = load_and_clean_data()

# ==============================================================================
# 🎛️ 前端網頁渲染與側邊欄
# ==============================================================================
if df_cleaned.empty or 'period' not in df_cleaned.columns:
    st.error("⚠️ 資料表欄位對齊失敗，請確認 CSV 檔案結構。")
else:
    st.sidebar.header("📊 數據篩選中心")

    # 1. 半年度期間篩選器
    all_periods = sorted([x for x in df_cleaned['period'].unique() if x != "Unknown"])
    if all_periods:
        selected_period = st.sidebar.selectbox("選擇報告期間 (Period)", all_periods, index=len(all_periods)-1)
    else:
        selected_period = "Unknown"

    # 2. 船舶類型篩選器
    all_vessels = sorted(list(df_cleaned['vessel_type'].unique()))
    default_vessels = [v for v in ["All_Vessel_Types", "Container ships", "Liquid bulk carriers"] if v in all_vessels]
    if not default_vessels:
        default_vessels = all_vessels[:2] if len(all_vessels) > 0 else all_vessels

    selected_vessels = st.sidebar.multiselect("選擇船舶類型", all_vessels, default=default_vessels)

    # 3. 限制顯示的國家數量
    max_countries = st.sidebar.slider("畫面上顯示前幾名效率排行國家", min_value=5, max_value=40, value=15)

    # 動態過濾資料
    filtered_df = df_cleaned[
        (df_cleaned['period'] == selected_period) & 
        (df_cleaned['vessel_type'].isin(selected_vessels))
    ]

    # --- 主網頁畫面 ---
    st.title("⚓️ 全球海事港口績效動態儀表板")
    st.markdown(f"**當前分析期間： `{selected_period}`** | 本系統融合 Kaggle 開源 EDA 資料清洗技術，實現動態港口效率分析。")
    st.write("---")

    # 💡 第一層：折線圖
    st.header("📈 各經濟體港口停泊時間對比")
    
    if not filtered_df.empty:
        plot_df = filtered_df.sort_values(by='median_time_in_port', ascending=False).head(max_countries)
        
        try:
            fig_line = px.line(
                plot_df,
                x='economy_label',
                y='median_time_in_port',
                color='vessel_type',
                title=f"各經濟體船舶在港中位數時間排行 (前 {max_countries} 名)",
                labels={'economy_label': '經濟體/國家', 'median_time_in_port': '停泊中位數時間 (天)', 'vessel_type': '船舶類型'},
                markers=True,
                template="ggplot2"
            )
            
            max_y = float(plot_df['median_time_in_port'].max()) if not plot_df['median_time_in_port'].empty else 5.0
            fig_line.update_layout(
                xaxis_tickangle=-45, 
                height=600,
                yaxis_range=[0, max_y * 1.3]
            )
            st.plotly_chart(fig_line, use_container_width=True)
        except Exception as plot_error:
            st.error(f"❌ 渲染折線圖時發生錯誤: {plot_error}")
    else:
        st.warning("⚠️ 當前篩選條件下無數據，請在左側側邊欄重新勾選船舶類型。")

    st.write("---")

    # 💡 第二層：雙變量統計箱線圖
    st.header("📊 進階統計：船舶類型 vs 港口核心指標分佈 (Boxplot)")

    tab1, tab2 = st.tabs(["⏳ 在港停泊時間分佈", "🚢 船舶平均總噸位(GT)分佈"])

    with tab1:
        if not filtered_df.empty:
            try:
                fig_box1 = px.box(
                    filtered_df,
                    x='vessel_type',
                    y='median_time_in_port',
                    color='vessel_type',
                    title=f"不同船舶類型的港口停泊時間統計分佈 ({selected_period})",
                    labels={'vessel_type': '船舶類型', 'median_time_in_port': '在港時間 (天)'},
                    points="all",
                    template="ggplot2"
                )
                fig_box1.update_layout(height=500, showlegend=False)
                st.plotly_chart(fig_box1, use_container_width=True)
            except Exception as e:
                st.error(f"無法渲染停泊時間箱線圖: {e}")

    with tab2:
        if not filtered_df.empty:
            try:
                fig_box2 = px.box(
                    filtered_df,
                    x='vessel_type',
                    y='avg_size_GT',
                    color='vessel_type',
                    title=f"不同船舶類型的平均總噸位 (GT) 統計分佈 ({selected_period})",
                    labels={'vessel_type': '船舶類型', 'avg_size_GT': '平均總噸位 (GT)'},
                    points="all",
                    template="ggplot2"
                )
                fig_box2.update_layout(height=500, showlegend=False)
                st.plotly_chart(fig_box2, use_container_width=True)
            except Exception as e:
                st.error(f"無法渲染噸位箱線圖: {e}")

    # 底部數據檢查器
    with st.expander("🔍 檢視當前動態資料集摘要"):
        st.dataframe(filtered_df)
