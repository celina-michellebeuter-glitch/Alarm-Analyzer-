import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO

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

        # --- CLEANING & MAPPING ---
        df.columns = [c.strip() for c in df.columns]
        SEL_COUNTRY = "COUNTRY"
        SEL_REGION = "REGION"
        SEL_TIME = "ALARM TIMESTAMP"

        if SEL_COUNTRY not in df.columns or SEL_TIME not in df.columns:
            st.error(f"Required columns missing!")
            st.stop()

        df[SEL_TIME] = pd.to_datetime(df[SEL_TIME], errors='coerce')
        df = df.dropna(subset=[SEL_TIME]).sort_values(by=SEL_TIME)

        # --- FIXED COLOR MAPPING ---
        # Wir erstellen eine feste Farbpalette für alle Länder, damit sie überall gleich bleiben
        unique_countries = sorted(df[SEL_COUNTRY].unique().tolist())
        color_palette = px.colors.qualitative.Prism + px.colors.qualitative.Safe # Große Palette
        color_map = {country: color_palette[i % len(color_palette)] for i, country in enumerate(unique_countries)}

        # ---------------------------------------------------------
        # SECTION 1: QUICK SUMMARY
        # ---------------------------------------------------------
        st.header("1. Quick Summary")
        m1, m2 = st.columns(2)
        m1.metric("Total Alarms", len(df))
        m2.metric("Countries Affected", df[SEL_COUNTRY].nunique())

        st.divider()
        col_chart, col_stat = st.columns([2, 1])
        
        # Stats berechnen
        stats_full = df[SEL_COUNTRY].value_counts().reset_index()
        stats_full.columns = [SEL_COUNTRY, 'Count']
        stats_full['Percentage'] = (stats_full['Count'] / stats_full['Count'].sum() * 100).round(2)
        stats_full['Percentage'] = stats_full['Percentage'].astype(str) + " %"

        with col_chart:
            fig_pie = px.pie(stats_full, values='Count', names=SEL_COUNTRY, hole=0.5, 
                             title="Overall Country Distribution",
                             color=SEL_COUNTRY, color_discrete_map=color_map)
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_pie, use_container_width=True)
            
        with col_stat:
            st.write("### Statistics per Country")
            st.dataframe(stats_full, use_container_width=True, hide_index=True)

        # ---------------------------------------------------------
        # SECTION 2: TIMELINE ANALYSIS
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
            color_target = base_col
            if extra_color:
                color_target = st.selectbox("Choose Category to compare:", [c for c in df.columns if c != SEL_TIME and c != base_col])

        # Grouping Logic
        if time_view == "Day": df_timeline['Time Period'] = df_timeline[SEL_TIME].dt.date
        elif time_view == "Week": df_timeline['Time Period'] = df_timeline[SEL_TIME].dt.to_period('W').apply(lambda r: r.start_time)
        elif time_view == "Month": df_timeline['Time Period'] = df_timeline[SEL_TIME].dt.to_period('M').apply(lambda r: r.start_time)
        else: df_timeline['Time Period'] = df_timeline[SEL_TIME]

        group_cols = ['Time Period', base_col]
        if extra_color: group_cols.append(color_target)
        timeline_data = df_timeline.groupby(group_cols).size().reset_index(name='Alarms')
        
        # Line Chart mit der festen Farbkarte
        fig_line = px.line(timeline_data, x='Time Period', y='Alarms', color=color_target,
                           markers=True, title=f"Timeline Trends",
                           # Wir nutzen color_discrete_map nur, wenn nach Country gefärbt wird
                           color_discrete_map=color_map if color_target == SEL_COUNTRY else None,
                           custom_data=[base_col] if extra_color else None)

        hover_content = f"<b>{filter_type}:</b> %{{customdata[0]}}<br>" if extra_color else ""
        hover_content += f"<b>{color_target}:</b> %{{fullData.name}}<br><b>Exact Time:</b> %{{x|%d.%m.%Y %H:%M:%S}}<br><b>Alarms:</b> %{{y}}<extra></extra>"
        fig_line.update_traces(hovertemplate=hover_content)
        fig_line.update_xaxes(rangeslider_visible=True, tickformat="%d.%m.\n%H:%M")
        st.plotly_chart(fig_line, use_container_width=True)

        # ---------------------------------------------------------
        # SECTION 3: DEEP DIVE
        # ---------------------------------------------------------
        st.divider()
        with st.expander("🔍 Deep Dive & Export"):
            st.subheader("Filtered Data Explorer")
            # Wir zeigen die Daten an, die in Sektion 2 gefiltert wurden
            df_export = df_timeline.drop(columns=['Time Period']) if 'Time Period' in df_timeline.columns else df_timeline
            st.dataframe(df_export, use_container_width=True, hide_index=True)
            
            # Excel Export
            output_excel = BytesIO()
            with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
                df_export.to_excel(writer, index=False)
            st.download_button("📥 Download filtered data as Excel", data=output_excel.getvalue(), file_name="alarm_export.xlsx")

    except Exception as e:
        st.error(f"Error: {e}")
else:
    st.info("Please upload a file to start.")
