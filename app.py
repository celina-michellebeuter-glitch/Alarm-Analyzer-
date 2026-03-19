import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Page Configuration
st.set_page_config(page_title="Ultimate Data Analyzer", layout="wide")

st.title("🔍 Multi-Dimensional Alarm Analyzer")
st.markdown("Compare countries, modules, and error codes with dynamic filters.")

# 2. File Upload
uploaded_file = st.file_uploader("Upload CSV or Excel", type=["csv", "xlsx"])

if uploaded_file is not None:
    try:
        # Load data
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, sep=None, engine='python')
        else:
            df = pd.read_excel(uploaded_file)

        st.success(f"✅ Loaded {len(df)} entries.")
        
        # --- SIDEBAR: DYNAMIC SETTINGS ---
        st.sidebar.header("⚙️ Global Mapping")
        all_cols = list(df.columns)

        # Smart detection for core columns
        def guess(opts, keys):
            for k in keys:
                for o in opts:
                    if k.lower() in str(o).lower(): return o
            return opts[0]

        sel_country = st.sidebar.selectbox("Primary Category (e.g. COUNTRY)", all_cols, 
            index=all_cols.index(guess(all_cols, ["country", "land", "region"])))
        
        sel_time = st.sidebar.selectbox("Timestamp Column", all_cols, 
            index=all_cols.index(guess(all_cols, ["time", "timestamp", "date"])))

        st.sidebar.divider()
        st.sidebar.header("🎯 Dynamic Filters")
        
        # Select columns to filter by
        filter_cols = st.sidebar.multiselect("Add Filters for:", 
                                            [c for c in all_cols if c != sel_time],
                                            default=[sel_country])

        df_f = df.copy()
        for col in filter_cols:
            unique_vals = sorted(df[col].dropna().unique().tolist())
            selected_vals = st.sidebar.multiselect(f"Filter {col}", unique_vals, default=unique_vals)
            df_f = df_f[df_f[col].isin(selected_vals)]

        # 3. Data Processing
        df_f[sel_time] = pd.to_datetime(df_f[sel_time], errors='coerce')
        df_f = df_f.dropna(subset=[sel_time]).sort_values(by=sel_time)

        # --- DASHBOARD METRICS ---
        st.divider()
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Alarms (Filtered)", len(df_f))
        m2.metric("Active Groups", df_f[sel_country].nunique())
        
        if len(filter_cols) > 0:
            m3.metric(f"Top {filter_cols[0]}", df_f[filter_cols[0]].mode()[0] if not df_f.empty else "N/A")

        # --- ANALYSIS 1: COMPARISON CHART ---
        st.header("1. Cross-Category Comparison")
        # Hier war der Fehler: all_cols statt all_columns
        comp_col = st.selectbox("Compare with which Category?", [c for c in all_cols if c != sel_time], 
                                index=0)
        
        fig_comp = px.histogram(df_f, x=sel_country, color=comp_col, barmode="group",
                                title=f"Comparison: {sel_country} vs {comp_col}",
                                text_auto=True)
        st.plotly_chart(fig_comp, use_container_width=True)

        # --- ANALYSIS 2: NATURAL TIMELINE ---
        st.divider()
        st.header("2. Timeline & Trends")
        
        color_by = st.selectbox("Color Timeline by:", filter_cols if filter_cols else [sel_country], index=0)
        
        timeline = df_f.groupby([sel_time, color_by]).size().reset_index(name='Alarms')
        
        fig_line = px.scatter(timeline, x=sel_time, y='Alarms', color=color_by,
                           title=f"Events over Time (Colored by {color_by})")
        
        fig_line.update_traces(mode='lines+markers', marker=dict(size=8))
        fig_line.update_xaxes(rangeslider_visible=True)
        fig_line.update_layout(hovermode="x unified")
        st.plotly_chart(fig_line, use_container_width=True)

        # --- DOWNLOAD SECTION ---
        st.divider()
        st.subheader("📥 Export Results")
        csv = df_f.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Filtered Data as CSV",
            data=csv,
            file_name="filtered_alarm_data.csv",
            mime="text/csv",
        )

        with st.expander("Raw Data Preview"):
            st.dataframe(df_f, use_container_width=True)

    except Exception as e:
        st.error(f"Analysis Error: {e}")
else:
    st.info("Upload a file to unlock advanced comparisons.")
