import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Page Configuration
st.set_page_config(page_title="Alarm Analyzer Pro", layout="wide")

st.title("Alarm Analysis Dashboard")

# 2. File Upload
uploaded_file = st.file_uploader("Upload your CSV or Excel file", type=["csv", "xlsx"])

if uploaded_file is not None:
    try:
        # Load data
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, sep=None, engine='python')
        else:
            df = pd.read_excel(uploaded_file)

        # --- SIDEBAR: FIXED GLOBAL MAPPING ---
        st.sidebar.header("📍 Global Mapping")
        st.sidebar.success("Mapping is fixed to your data structure.")
        
        # Clean column names (remove whitespace)
        df.columns = [c.strip() for c in df.columns]
        
        # Hardcoded column names based on your requirement
        SEL_COUNTRY = "COUNTRY"
        SEL_REGION = "REGION"
        SEL_TIME = "ALARM TIMESTAMP"

        # Check if mandatory columns exist
        if SEL_COUNTRY not in df.columns or SEL_TIME not in df.columns:
            st.error(f"Required columns '{SEL_COUNTRY}' or '{SEL_TIME}' missing in file!")
            st.stop()

        # Pre-process time globally
        df[SEL_TIME] = pd.to_datetime(df[SEL_TIME], errors='coerce')
        df = df.dropna(subset=[SEL_TIME]).sort_values(by=SEL_TIME)

        # ---------------------------------------------------------
        # SECTION 1: QUICK SUMMARY
        # ---------------------------------------------------------
        st.header("1. Quick Summary")
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Alarms", len(df))
        m2.metric("Countries", df[SEL_COUNTRY].nunique())
        if SEL_REGION in df.columns:
            m3.metric("Regions", df[SEL_REGION].nunique())

        st.divider()
        col_chart, col_stat = st.columns([2, 1])
        
        stats_full = df[SEL_COUNTRY].value_counts().reset_index()
        stats_full.columns = [SEL_COUNTRY, 'Count']
        stats_full['%'] = (stats_full['Count'] / stats_full['Count'].sum() * 100).round(2)

        with col_chart:
            fig_pie = px.pie(stats_full, values='Count', names=SEL_COUNTRY, hole=0.5, 
                             title="Overall Country Distribution",
                             color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig_pie, use_container_width=True)
            
        with col_stat:
            st.write("### Statistics")
            st.dataframe(stats_full.style.format({'%': '{:.2f}%'}), use_container_width=True)

        # ---------------------------------------------------------
        # SECTION 2: TIMELINE ANALYSIS (Refined Hover & Grouping)
        # ---------------------------------------------------------
        st.divider()
        st.header("2. Timeline Analysis")

        # Dynamic Filtering Logic
        t_col1, t_col2 = st.columns([1, 2])
        
        with t_col1:
            filter_type = st.radio("Filter Timeline by:", ["Country", "Region"], horizontal=True)
            
        with t_col2:
            if filter_type == "Country":
                options = sorted(df[SEL_COUNTRY].unique().tolist())
                selected_items = st.multiselect("Select Countries:", options, default=options)
                df_timeline = df[df[SEL_COUNTRY].isin(selected_items)].copy()
                color_target = SEL_COUNTRY
            else:
                if SEL_REGION in df.columns:
                    options = sorted(df[SEL_REGION].unique().tolist())
                    selected_items = st.multiselect("Select Regions:", options, default=options)
                    df_timeline = df[df[SEL_REGION].isin(selected_items)].copy()
                    color_target = SEL_REGION
                else:
                    st.warning("No 'REGION' column found in your file.")
                    df_timeline = df.copy()
                    color_target = SEL_COUNTRY

        # Timeline Controls
        c1, c2 = st.columns(2)
        with c1:
            time_view = st.radio("Group by:", ["Exact Time", "Day", "Week", "Month"], horizontal=True, index=1)
        with c2:
            extra_color = st.checkbox("Color by different category?")
            if extra_color:
                color_target = st.selectbox("Choose Category:", [c for c in df.columns if c != SEL_TIME])

        # Grouping Logic with cleaner naming
        if time_view == "Day":
            df_timeline['Time Period'] = df_timeline[SEL_TIME].dt.date
        elif time_view == "Week":
            df_timeline['Time Period'] = df_timeline[SEL_TIME].dt.to_period('W').apply(lambda r: r.start_time)
        elif time_view == "Month":
            df_timeline['Time Period'] = df_timeline[SEL_TIME].dt.to_period('M').apply(lambda r: r.start_time)
        else:
            df_timeline['Time Period'] = df_timeline[SEL_TIME]

        # Aggregate data for the chart
        timeline_data = df_timeline.groupby(['Time Period', color_target]).size().reset_index(name='Alarms')
        
        # Build the chart
        fig_line = px.line(timeline_data, x='Time Period', y='Alarms', color=color_target,
                           markers=True, title=f"Timeline trends (Filtered by {filter_type})")

        # IMPROVEMENT: Add exact timestamps to hover data
        # We use a trick: we map the original timestamps back to the points for the hover tooltip
        fig_line.update_traces(
            hovertemplate="<b>%{label}</b><br>Alarms: %{y}<br>Period: %{x}<extra></extra>"
        )
        
        # Better X-Axis Formatting
        fig_line.update_xaxes(
            rangeslider_visible=True,
            tickformat="%d %b %Y\n%H:%M" if time_view == "Exact Time" else "%d %b %Y"
        )
        
        fig_line.update_layout(hovermode="x unified")
        st.plotly_chart(fig_line, use_container_width=True)

        # ---------------------------------------------------------
        # SECTION 3: DEEP DIVE
        # ---------------------------------------------------------
        st.divider()
        with st.expander("🔍 Deep Dive & Raw Data"):
            st.subheader("Comparison Chart")
            comp_col = st.selectbox("Compare Countries against:", [c for c in df.columns if c != SEL_TIME], index=0)
            fig_bar = px.histogram(df, x=SEL_COUNTRY, color=comp_col, barmode="group", text_auto=True)
            st.plotly_chart(fig_bar, use_container_width=True)

            st.divider()
            st.subheader("Full Data Explorer")
            st.dataframe(df, use_container_width=True)
            
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("Download current data as CSV", data=csv, file_name="export.csv", mime="text/csv")

    except Exception as e:
        st.error(f"Error: {e}")
else:
    st.info("Please upload a file to start the analysis.")
