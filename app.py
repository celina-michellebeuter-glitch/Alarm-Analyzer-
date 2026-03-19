import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Page Configuration
st.set_page_config(page_title="Alarm Analyzer Pro", layout="wide")

st.title("📊 Alarm Dashboard")
st.markdown("Immediate overview of your device status and global distribution.")

# 2. File Upload
uploaded_file = st.file_uploader("Upload CSV or Excel", type=["csv", "xlsx"])

if uploaded_file is not None:
    try:
        # Load data
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, sep=None, engine='python')
        else:
            df = pd.read_excel(uploaded_file)

        # --- SIDEBAR: GLOBAL MAPPING & FILTERS ---
        st.sidebar.header("📍 Global Mapping")
        all_cols = list(df.columns)

        def guess(opts, keys):
            for k in keys:
                for o in opts:
                    if k.lower() in str(o).lower(): return o
            return opts[0]

        sel_country = st.sidebar.selectbox("Primary Category (Country)", all_cols, 
            index=all_cols.index(guess(all_cols, ["country", "land", "region"])))
        
        sel_time = st.sidebar.selectbox("Timestamp Column", all_cols, 
            index=all_cols.index(guess(all_cols, ["time", "timestamp", "date"])))

        st.sidebar.divider()
        st.sidebar.header("🎯 Global Filters")
        
        available_filter_cols = [c for c in all_cols if c != sel_time]
        filter_selection = st.sidebar.multiselect("Active Filters:", available_filter_cols, default=[sel_country])

        df_f = df.copy()
        for col in filter_selection:
            unique_vals = sorted(df[col].dropna().unique().tolist())
            selected_vals = st.sidebar.multiselect(f"Filter {col}", unique_vals, default=unique_vals)
            df_f = df_f[df_f[col].isin(selected_vals)]

        # Processing Time
        df_f[sel_time] = pd.to_datetime(df_f[sel_time], errors='coerce')
        df_f = df_f.dropna(subset=[sel_time]).sort_values(by=sel_time)

        # ---------------------------------------------------------
        # SECTION 1: QUICK SUMMARY (TOP)
        # ---------------------------------------------------------
        st.header("1. Quick Summary")
        m1, m2 = st.columns(2)
        m1.metric("Total Alarms", len(df_f))
        m2.metric("Countries Affected", df_f[sel_country].nunique())

        st.divider()
        col_chart, col_stat = st.columns([2, 1])
        
        stats = df_f[sel_country].value_counts().reset_index()
        stats.columns = [sel_country, 'Count']
        stats['%'] = (stats['Count'] / stats['Count'].sum() * 100).round(2)

        with col_chart:
            fig_pie = px.pie(stats, values='Count', names=sel_country, hole=0.5, 
                             title=f"Global Distribution by {sel_country}",
                             color_discrete_sequence=px.colors.qualitative.Pastel)
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_pie, use_container_width=True)
            
        with col_stat:
            st.write("### Quick Stats Table")
            st.dataframe(stats.style.format({'%': '{:.2f}%'}), use_container_width=True)

        # ---------------------------------------------------------
        # SECTION 2: TIMELINE ANALYSIS (WITH LOCAL COUNTRY FILTER)
        # ---------------------------------------------------------
        st.divider()
        st.header("2. Timeline Analysis")
        
        # Local Filter for Timeline
        countries_in_data = sorted(df_f[sel_country].unique().tolist())
        selected_timeline_countries = st.multiselect(
            f"Select {sel_country} for Timeline View:", 
            options=countries_in_data, 
            default=countries_in_data
        )

        # Apply Local Filter to Timeline Data
        df_timeline_filtered = df_f[df_f[sel_country].isin(selected_timeline_countries)].copy()

        t_col1, t_col2 = st.columns(2)
        with t_col1:
            color_by_opt = st.selectbox("Color timeline by:", filter_selection if filter_selection else [sel_country])
        with t_col2:
            time_view = st.radio("Group timeline by:", ["Exact Time", "Day", "Week", "Month", "Year"], horizontal=True, index=1)

        # Grouping Logic
        if time_view == "Day":
            df_timeline_filtered['Time_Group'] = df_timeline_filtered[sel_time].dt.date
        elif time_view == "Week":
            df_timeline_filtered['Time_Group'] = df_timeline_filtered[sel_time].dt.to_period('W').apply(lambda r: r.start_time)
        elif time_view == "Month":
            df_timeline_filtered['Time_Group'] = df_timeline_filtered[sel_time].dt.to_period('M').apply(lambda r: r.start_time)
        elif time_view == "Year":
            df_timeline_filtered['Time_Group'] = df_timeline_filtered[sel_time].dt.to_period('Y').apply(lambda r: r.start_time)
        else:
            df_timeline_filtered['Time_Group'] = df_timeline_filtered[sel_time]

        timeline_data = df_timeline_filtered.groupby(['Time_Group', color_by_opt]).size().reset_index(name='Alarms')
        
        fig_line = px.line(timeline_data, x='Time_Group', y='Alarms', color=color_by_opt,
                           markers=True, title=f"Trends for selected {sel_country}")
        
        fig_line.update_xaxes(rangeslider_visible=True, title="Time")
        fig_line.update_layout(hovermode="x unified")
        st.plotly_chart(fig_line, use_container_width=True)

        # ---------------------------------------------------------
        # SECTION 3: DEEP DIVE
        # ---------------------------------------------------------
        st.divider()
        with st.expander("🔍 Deep Dive: Cross-Comparison & Raw Data"):
            c_left, c_right = st.columns(2)
            with c_left:
                st.subheader("Comparison Chart")
                comp_target = st.selectbox("Compare Countries against:", [c for c in all_cols if c != sel_time], index=0)
                fig_bar = px.histogram(df_f, x=sel_country, color=comp_target, barmode="group", text_auto=True)
                st.plotly_chart(fig_bar, use_container_width=True)
            with c_right:
                st.subheader("Data Export")
                csv = df_f.to_csv(index=False).encode('utf-8')
                st.download_button("Download filtered CSV", data=csv, file_name="analysis_export.csv", mime="text/csv")

            st.subheader("Full Data Explorer")
            st.dataframe(df_f, use_container_width=True)

    except Exception as e:
        st.error(f"Something went wrong: {e}")
else:
    st.info("Please upload your CSV or Excel file to see the analysis.")
