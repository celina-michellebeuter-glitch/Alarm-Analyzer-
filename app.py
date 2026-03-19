import streamlit as st
import pandas as pd
import plotly.express as px

# Basic Page Configuration
st.set_page_config(page_title="Global Alarm Analyzer", layout="wide")

st.title("📊 Global Alarm & Device Analyzer")
st.markdown("""
This tool analyzes device alarms from CSV or Excel files. 
It calculates the distribution per country and shows the timeline of events.
""")

# 1. File Upload
uploaded_file = st.file_uploader("Upload your data file (CSV or Excel)", type=["csv", "xlsx"])

if uploaded_file is not None:
    try:
        # Load data with automatic separator detection for CSV
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, sep=None, engine='python')
        else:
            df = pd.read_excel(uploaded_file)

        st.success(f"✅ File loaded successfully! ({len(df)} rows found)")
        
        # 2. Flexible Column Selection in Sidebar
        st.sidebar.header("⚙️ Settings")
        st.sidebar.write("Select the columns for analysis:")
        
        all_columns = list(df.columns)

        # Smart helper to guess the correct column based on keywords
        def guess_col(options, keywords):
            for k in keywords:
                for opt in options:
                    if k.lower() in str(opt).lower():
                        return opt
            return options[0]

        # User chooses the columns (pre-selected by smart guessing)
        sel_country = st.sidebar.selectbox(
            "Which column represents the COUNTRY?", 
            all_columns, 
            index=all_columns.index(guess_col(all_columns, ["country", "land", "region", "nation"]))
        )

        sel_time = st.sidebar.selectbox(
            "Which column represents the TIMESTAMP?", 
            all_columns, 
            index=all_columns.index(guess_col(all_columns, ["time", "date", "timestamp", "datum", "at"]))
        )

        # 3. Data Processing
        # Convert to datetime and drop rows with invalid dates
        df[sel_time] = pd.to_datetime(df[sel_time], errors='coerce')
        df = df.dropna(subset=[sel_time])

        # --- ANALYSIS 1: Devices/Alarms per Country ---
        st.divider()
        st.header(f"1. Distribution by {sel_country}")
        
        stats = df[sel_country].value_counts().reset_index()
        stats.columns = [sel_country, 'Alarm Count']
        stats['Percentage'] = (stats['Alarm Count'] / stats['Alarm Count'].sum() * 100).round(2)
        
        col1, col2 = st.columns([1, 2])
        with col1:
            st.subheader("Data Summary")
            # Display table with formatted percentage
            st.dataframe(stats.style.format({'Percentage': '{:.2f}%'}), use_container_width=True)
        with col2:
            fig_pie = px.pie(stats, values='Alarm Count', names=sel_country, 
                             hole=0.4, title=f"Proportional Distribution ({sel_country})",
                             color_discrete_sequence=px.colors.qualitative.Safe)
            st.plotly_chart(fig_pie, use_container_width=True)

        # --- ANALYSIS 2: Time Series ---
        st.divider()
        st.header(f"2. Alarm Timeline ({sel_time})")
        
        # Group by Date (Daily)
        df['Date_Only'] = df[sel_time].dt.date
        timeline = df.groupby(['Date_Only', sel_country]).size().reset_index(name='Alarms')
        
        fig_line = px.line(timeline, x='Date_Only', y='Alarms', color=sel_country,
                           markers=True, title="When did the alarms occur per country?",
                           labels={'Alarms': 'Number of Alarms', 'Date_Only': 'Date'})
        
        fig_line.update_layout(xaxis_title="Date", yaxis_title="Number of Alarms", hovermode="x unified")
        st.plotly_chart(fig_line, use_container_width=True)

        # Full Data Preview
        with st.expander("View Raw Data Details"):
            st.write("Sorted by timestamp:")
            st.dataframe(df.sort_values(by=sel_time), use_container_width=True)

    except Exception as e:
        st.error(f"❌ An error occurred during processing: {e}")
        st.info("Tip: Please ensure your file has headers in the first row.")

else:
    st.info("Please upload a file to begin the analysis.")
