import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Page Configuration
st.set_page_config(page_title="Custom Alarm Analyzer", layout="wide")

st.title("📊 Alarm Analysis Dashboard")

# 2. File Upload
uploaded_file = st.file_uploader("Upload your CSV or Excel file", type=["csv", "xlsx"])

if uploaded_file is not None:
    try:
        # Load data
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, sep=None, engine='python')
        else:
            df = pd.read_excel(uploaded_file)

        # --- SIDEBAR: GLOBAL MAPPING ONLY ---
        st.sidebar.header("📍 Global Mapping")
        st.sidebar.info("Define which columns represent your core data types.")
        all_cols = list(df.columns)

        def guess(opts, keys):
            for k in keys:
                for o in opts:
                    if k.lower() in str(o).lower(): return o
            return opts[0]

        sel_country = st.sidebar.selectbox("Primary Category (e.g. Country/Region)", all_cols, 
            index=all_cols.index(guess(all_cols, ["country", "land", "region"])))
        
        sel_time = st.sidebar.selectbox("Timestamp Column", all_cols, 
            index=all_cols.index(guess(all_cols, ["time", "timestamp", "date"])))

        # Pre-process time globally
        df[sel_time] = pd.to_datetime(df[sel_time], errors='coerce')
        df = df.dropna(subset=[sel_time]).sort_values(by=sel_time)

        # ---------------------------------------------------------
        # SECTION 1: QUICK SUMMARY (Unfiltered Overview)
        # ---------------------------------------------------------
        st.header("1. Quick Summary")
        m1, m2 = st.columns(2)
        m1.metric("Total Alarms in File", len(df))
        m2.metric("Total Countries/Regions", df[sel_country].nunique())

        st.divider()
        col_chart, col_stat = st.columns([2, 1])
        
        stats_full = df[sel_country].value_counts().reset_index()
        stats_full.columns = [sel_country, 'Count']
        stats_full['%'] = (stats_full['Count'] / stats_full['Count'].sum() * 100).round(2)

        with col_chart:
            fig_pie = px.pie(stats_full, values='Count', names=sel_country, hole=0.5, 
                             title="Overall Distribution",
                             color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig_pie, use_container_width=True)
            
        with col_stat:
            st.write("### Full Statistics")
            st.dataframe(stats_full.style.format({'%': '{:.2f}%'}), use_container_width=True)

        # ---------------------------------------------------------
        # SECTION 2: TIMELINE ANALYSIS (With Local Filters)
        # ---------------------------------------------------------
        st.divider()
        st.header("2. Timeline Analysis")
        st.markdown("Filter and group the data specifically for this timeline view.")

        # Local Filters for Timeline
        t_filter_row = st.container()
        with t_filter_row:
            # 1. Filter for Country/Region
            available_items = sorted(df[sel_country].unique().tolist())
            selected_items = st.multiselect(f"Filter {sel_country}:", 
                                            options=available_items, 
                                            default=available_items)
            
            # 2. Controls for View
            c1, c2, c3 = st.columns(3)
            with c1:
                # Dynamically allow coloring by any column
                color_by_opt = st.selectbox("Color lines by:", all_cols, 
                                            index=all_cols.index(sel_country))
            with c2:
                time_view = st.radio("Group by:", ["Exact Time", "Day", "Week", "Month"], horizontal=True, index=1)
            with c3:
                st.write("") # Spacer

        # Apply Local Filters
        df_timeline = df[df[sel_country].isin(selected_items)].copy()

        # Grouping Logic
        if time_view == "Day":
            df_timeline['Time_Group'] = df_timeline[sel_time].dt.date
        elif time_view == "Week":
            df_timeline['Time_Group'] = df_timeline[sel_time].dt.to_period('W').apply(lambda r: r.start_time)
        elif time_view == "Month":
            df_timeline['Time_Group'] = df_timeline[sel_time].dt.to_period('M').apply(lambda r: r.start_time)
        else:
            df_timeline['Time_Group'] = df_timeline[sel_time]

        timeline_data = df_timeline.groupby(['Time_Group', color_by_opt]).size().reset_index(name='Alarms')
        
        fig_line = px.line(timeline_data, x='Time_Group', y='Alarms', color=color_by_opt,
                           markers=True, title=f"Timeline of Alarms (Filtered)")
        fig_line.update_xaxes(rangeslider_visible=True)
        st.plotly_chart(fig_line, use_container_width=True)

        # ---------------------------------------------------------
        # SECTION 3: DEEP DIVE & RAW DATA
        # ---------------------------------------------------------
        st.divider()
        with st.expander("🔍 Deep Dive: Cross-Comparison & Data Table"):
            st.subheader("Comparison Chart")
            comp_col = st.selectbox("Compare primary category against:", [c for c in all_cols if c != sel_time], index=0)
            
            fig_bar = px.histogram(df, x=sel_country, color=comp_col, barmode="group", text_auto=True)
            st.plotly_chart(fig_bar, use_container_width=True)

            st.divider()
            st.subheader("Raw Data Table")
            st.dataframe(df, use_container_width=True)
            
            # Export
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("Download current data as CSV", data=csv, file_name="export.csv", mime="text/csv")

    except Exception as e:
        st.error(f"Error: {e}")
else:
    st.info("Please upload a file to start the analysis.")
