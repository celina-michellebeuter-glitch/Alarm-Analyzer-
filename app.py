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
        
        # Clean column names
        df.columns = [c.strip() for c in df.columns]
        
        SEL_COUNTRY = "COUNTRY"
        SEL_REGION = "REGION"
        SEL_TIME = "ALARM TIMESTAMP"

        if SEL_COUNTRY not in df.columns or SEL_TIME not in df.columns:
            st.error(f"Required columns '{SEL_COUNTRY}' or '{SEL_TIME}' missing!")
            st.stop()

        # Pre-process time
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
        # SECTION 2: TIMELINE ANALYSIS (Advanced Tooltip)
        # ---------------------------------------------------------
        st.divider()
        st.header("2. Timeline Analysis")

        # Dynamic Filtering
        t_col1, t_col2 = st.columns([1, 2])
        with t_col1:
            filter_type = st.radio("Filter Timeline by:", ["Country", "Region"], horizontal=True)
        with t_col2:
            base_col = SEL_COUNTRY if filter_type == "Country" else (SEL_REGION if SEL_REGION in df.columns else SEL_COUNTRY)
            items = sorted(df[base_col].unique().tolist())
            selected_items = st.multiselect(f"Select {filter_type}s:", items, default=items)
            
        df_timeline = df[df[base_col].isin(selected_items)].copy()

        # Timeline Controls
        c1, c2 = st.columns(2)
        with c1:
            time_view = st.radio("Group by:", ["Exact Time", "Day", "Week", "Month"], horizontal=True, index=0)
        with c2:
            extra_color = st.checkbox("Color by different category?")
            color_target = base_col # Default color is the filtered category
            if extra_color:
                color_target = st.selectbox("Choose Category to compare:", [c for c in df.columns if c != SEL_TIME and c != base_col])

        # Grouping Logic
        if time_view == "Day":
            df_timeline['Time Period'] = df_timeline[SEL_TIME].dt.date
        elif time_view == "Week":
            df_timeline['Time Period'] = df_timeline[SEL_TIME].dt.to_period('W').apply(lambda r: r.start_time)
        elif time_view == "Month":
            df_timeline['Time Period'] = df_timeline[SEL_TIME].dt.to_period('M').apply(lambda r: r.start_time)
        else:
            df_timeline['Time Period'] = df_timeline[SEL_TIME]

        # Aggregate data - we keep BOTH base_col and color_target for the hover info
        group_cols = ['Time Period', base_col]
        if extra_color:
            group_cols.append(color_target)
        
        timeline_data = df_timeline.groupby(group_cols).size().reset_index(name='Alarms')
        
        # Build Chart
        fig_line = px.line(timeline_data, x='Time Period', y='Alarms', color=color_target,
                           markers=True, title=f"Timeline Trends",
                           # Wir fügen das Basis-Land als zusätzliches Datenfeld für den Hover hinzu
                           custom_data=[base_col] if extra_color else None)

        # HOVER CUSTOMIZATION: Zeigt beides an
        hover_content = f"<b>{filter_type}:</b> %{{customdata[0]}}<br>" if extra_color else ""
        hover_content += f"<b>{color_target}:</b> %{{fullData.name}}<br>"
        hover_content += "<b>Exact Time:</b> %{x|%d.%m.%Y %H:%M:%S}<br>"
        hover_content += "<b>Alarms:</b> %{y}<extra></extra>"

        fig_line.update_traces(hovertemplate=hover_content)
        
        fig_line.update_xaxes(rangeslider_visible=True, tickformat="%d.%m.\n%H:%M")
        fig_line.update_layout(hovermode="x unified")
        st.plotly_chart(fig_line, use_container_width=True)

        # ---------------------------------------------------------
        # SECTION 3: DEEP DIVE
        # ---------------------------------------------------------
        st.divider()
        with st.expander("🔍 Deep Dive & Raw Data"):
            st.subheader("Full Data Explorer")
            st.dataframe(df, use_container_width=True)
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("Download CSV", data=csv, file_name="export.csv", mime="text/csv")

    except Exception as e:
        st.error(f"Error: {e}")
else:
    st.info("Please upload a file to start the analysis.")
