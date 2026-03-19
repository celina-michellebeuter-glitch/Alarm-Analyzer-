import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Page Configuration
st.set_page_config(page_title="Advanced Alarm Analyzer", layout="wide")

st.title("🚀 Advanced Global Alarm Analyzer")
st.markdown("Analyze your device data with high precision and custom filters.")

# 2. File Upload
uploaded_file = st.file_uploader("Upload your data file (CSV or Excel)", type=["csv", "xlsx"])

if uploaded_file is not None:
    try:
        # Load data with automatic separator detection
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, sep=None, engine='python')
        else:
            df = pd.read_excel(uploaded_file)

        st.success(f"✅ Data loaded: {len(df)} rows")
        
        # --- SIDEBAR SETTINGS ---
        st.sidebar.header("⚙️ Column Mapping")
        all_columns = list(df.columns)

        def guess_col(options, keywords):
            for k in keywords:
                for opt in options:
                    if k.lower() in str(opt).lower():
                        return opt
            return options[0]

        sel_country = st.sidebar.selectbox("Country Column", all_columns, 
            index=all_columns.index(guess_col(all_columns, ["country", "land"])))
        
        sel_time = st.sidebar.selectbox("Timestamp Column", all_columns, 
            index=all_columns.index(guess_col(all_columns, ["time", "timestamp", "date"])))
        
        sel_sn = st.sidebar.selectbox("Device ID / Serial Number (Optional)", ["None"] + all_columns)

        st.sidebar.divider()
        st.sidebar.header("🔍 Filters & Precision")
        
        # Time Precision Setting
        time_granularity = st.sidebar.radio("Time Precision", 
                                          ["Hourly", "Daily", "Weekly"], index=0) # Default to Hourly for precision
        
        # Dynamic Filter for Countries
        unique_countries = sorted(df[sel_country].unique().tolist())
        selected_countries = st.sidebar.multiselect("Filter Countries", unique_countries, default=unique_countries)

        # Apply Country Filter
        df_filtered = df[df[sel_country].isin(selected_countries)].copy()

        # 3. Data Processing (Precision Fix)
        df_filtered[sel_time] = pd.to_datetime(df_filtered[sel_time], errors='coerce')
        df_filtered = df_filtered.dropna(subset=[sel_time])

        # Logic for accurate Time Buckets
        if time_granularity == "Hourly":
            df_filtered['Time_Bucket'] = df_filtered[sel_time].dt.floor('h')
        elif time_granularity == "Weekly":
            df_filtered['Time_Bucket'] = df_filtered[sel_time].dt.to_period('W').apply(lambda r: r.start_time)
        else:
            # Daily: Convert back to datetime to keep Plotly axis clean
            df_filtered['Time_Bucket'] = pd.to_datetime(df_filtered[sel_time].dt.date)

        # --- DASHBOARD METRICS ---
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Alarms", len(df_filtered))
        m2.metric("Countries Shown", len(selected_countries))
        if sel_sn != "None":
            m3.metric("Unique Devices", df_filtered[sel_sn].nunique())
        else:
            m3.metric("Unique Devices", "N/A")

        # --- ANALYSIS 1: Distribution ---
        st.divider()
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.subheader("Distribution Stats")
            stats = df_filtered[sel_country].value_counts().reset_index()
            stats.columns = [sel_country, 'Alarms']
            stats['%'] = (stats['Alarms'] / stats['Alarms'].sum() * 100).round(2)
            st.dataframe(stats, use_container_width=True)
            
        with col2:
            fig_pie = px.pie(stats, values='Alarms', names=sel_country, hole=0.4, 
                             title=f"Alarms per {sel_country}", color_discrete_sequence=px.colors.qualitative.Bold)
            st.plotly_chart(fig_pie, use_container_width=True)

        # --- ANALYSIS 2: Precise Timeline ---
        st.divider()
        st.header(f"Timeline Analysis ({time_granularity} Precision)")
        
        timeline = df_filtered.groupby(['Time_Bucket', sel_country]).size().reset_index(name='Count')
        
        # Ensure Time_Bucket is sorted for the line chart
        timeline = timeline.sort_values('Time_Bucket')
        
        fig_line = px.line(timeline, x='Time_Bucket', y='Count', color=sel_country, markers=True,
                           title="Alarm Trends Over Time",
                           labels={'Count': 'Number of Alarms', 'Time_Bucket': 'Time'})
        
        # Improvement: Custom Date Format on X-Axis
        fig_line.update_xaxes(
            dtick=3600000 if time_granularity == "Hourly" else None, # Tick every hour if hourly
            tickformat="%d %b %Y\n%H:%M" if time_granularity == "Hourly" else "%d %b %Y"
        )
        
        fig_line.update_layout(hovermode="x unified")
        st.plotly_chart(fig_line, use_container_width=True)

        # 4. Raw Data Table
        with st.expander("Show Detailed Data Table"):
            st.dataframe(df_filtered.sort_values(by=sel_time), use_container_width=True)

    except Exception as e:
        st.error(f"❌ Error during processing: {e}")

else:
    st.info("Please upload a CSV or Excel file to start.")
