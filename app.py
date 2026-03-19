import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO
from fpdf import FPDF

# 1. Page Configuration
st.set_page_config(page_title="Alarm Analyzer Pro", layout="wide")

st.title("Alarm Analysis Dashboard")

# Hilfsfunktion für PDF-Erstellung
def create_pdf(dataframe):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(40, 10, "Alarm Analysis Report")
    pdf.ln(20)
    pdf.set_font("Arial", size=10)
    
    # Schreibe die ersten 20 Zeilen (für ein vollständiges PDF-Reporting wäre mehr Logik nötig)
    for i in range(min(len(dataframe), 50)):
        row_str = ", ".join([str(val) for val in dataframe.iloc[i].values])
        pdf.multi_cell(0, 10, row_str)
    return pdf.output(dest='S').encode('latin-1')

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
        df.columns = [c.strip() for c in df.columns]
        
        SEL_COUNTRY = "COUNTRY"
        SEL_REGION = "REGION"
        SEL_TIME = "ALARM TIMESTAMP"

        if SEL_COUNTRY not in df.columns or SEL_TIME not in df.columns:
            st.error(f"Required columns '{SEL_COUNTRY}' or '{SEL_TIME}' missing!")
            st.stop()

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
        
        with col_chart:
            fig_pie = px.pie(stats_full, values='Count', names=SEL_COUNTRY, hole=0.5, 
                             title="Overall Country Distribution")
            st.plotly_chart(fig_pie, use_container_width=True)
        with col_stat:
            st.write("### Statistics")
            st.dataframe(stats_full, use_container_width=True)

        # ---------------------------------------------------------
        # SECTION 2: TIMELINE ANALYSIS
        # ---------------------------------------------------------
        st.divider()
        st.header("2. Timeline Analysis")
        
        t_col1, t_col2 = st.columns([1, 2])
        with t_col1:
            filter_type = st.radio("Filter Timeline by:", ["Country", "Region"], horizontal=True)
        with t_col2:
            base_col = SEL_COUNTRY if filter_type == "Country" else (SEL_REGION if SEL_REGION in df.columns else SEL_COUNTRY)
            items = sorted(df[base_col].unique().tolist())
            selected_items = st.multiselect(f"Select {filter_type}s:", items, default=items)
            
        df_timeline = df[df[base_col].isin(selected_items)].copy()

        c1, c2 = st.columns(2)
        with c1:
            time_view = st.radio("Group by:", ["Exact Time", "Day", "Week", "Month"], horizontal=True, index=0)
        with c2:
            extra_color = st.checkbox("Color by different category?")
            color_target = base_col
            if extra_color:
                color_target = st.selectbox("Choose Category to compare:", [c for c in df.columns if c != SEL_TIME and c != base_col])

        if time_view == "Day": df_timeline['Time Period'] = df_timeline[SEL_TIME].dt.date
        elif time_view == "Week": df_timeline['Time Period'] = df_timeline[SEL_TIME].dt.to_period('W').apply(lambda r: r.start_time)
        elif time_view == "Month": df_timeline['Time Period'] = df_timeline[SEL_TIME].dt.to_period('M').apply(lambda r: r.start_time)
        else: df_timeline['Time Period'] = df_timeline[SEL_TIME]

        group_cols = ['Time Period', base_col]
        if extra_color: group_cols.append(color_target)
        timeline_data = df_timeline.groupby(group_cols).size().reset_index(name='Alarms')
        
        fig_line = px.line(timeline_data, x='Time Period', y='Alarms', color=color_target, markers=True,
                           custom_data=[base_col] if extra_color else None)

        hover_content = f"<b>{filter_type}:</b> %{{customdata[0]}}<br>" if extra_color else ""
        hover_content += f"<b>{color_target}:</b> %{{fullData.name}}<br><b>Exact Time:</b> %{{x|%d.%m.%Y %H:%M:%S}}<br><b>Alarms:</b> %{{y}}<extra></extra>"
        fig_line.update_traces(hovertemplate=hover_content)
        fig_line.update_xaxes(rangeslider_visible=True, tickformat="%d.%m.\n%H:%M")
        st.plotly_chart(fig_line, use_container_width=True)

        # ---------------------------------------------------------
        # SECTION 3: DEEP DIVE & EXPORT
        # ---------------------------------------------------------
        st.divider()
        with st.expander("Uploaded Data & Download Informations"):
            st.subheader("Data Explorer")
            # Wir nutzen die gefilterten Daten der Timeline für den Export
            df_export = df_timeline.drop(columns=['Time Period']) if 'Time Period' in df_timeline.columns else df_timeline
            st.dataframe(df_export, use_container_width=True)
            
            st.write("### Choose Export Format")
            ex_col1, ex_col2, ex_col3 = st.columns(3)
            
            # CSV Export
            csv = df_export.to_csv(index=False).encode('utf-8')
            ex_col1.download_button("📥 Download as CSV", data=csv, file_name="alarm_export.csv", mime="text/csv")
            
            # Excel Export
            output_excel = BytesIO()
            with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
                df_export.to_excel(writer, index=False, sheet_name='Alarms')
            ex_col2.download_button("📥 Download as Excel", data=output_excel.getvalue(), file_name="alarm_export.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            
            # PDF Export (Basic)
            try:
                pdf_data = create_pdf(df_export)
                ex_col3.download_button("📥 Download as PDF (Table)", data=pdf_data, file_name="alarm_export.pdf", mime="application/pdf")
            except:
                ex_col3.warning("PDF-Export limited due to encoding.")

    except Exception as e:
        st.error(f"Error: {e}")
else:
    st.info("Please upload a file to start.")
