import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO
from fpdf import FPDF

# 1. Page Configuration
st.set_page_config(page_title="Alarm Analyzer Pro", layout="wide")

st.title("📊 Alarm Analysis Dashboard")

# --- PDF Helper ---
def create_pdf(df_summary, df_details):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Alarm Analysis Executive Report", ln=True, align='C')
    pdf.ln(10)
    # Zusammenfassung
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "1. Summary by Country", ln=True)
    pdf.set_font("Arial", size=10)
    for i in range(len(df_summary)):
        line = f"{df_summary.iloc[i, 0]}: {df_summary.iloc[i, 1]} Alarms"
        pdf.cell(0, 8, line, ln=True)
    return pdf.output(dest='S').encode('latin-1')

# 2. File Upload
uploaded_file = st.file_uploader("Upload your CSV or Excel file", type=["csv", "xlsx"])

if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, sep=None, engine='python')
        else:
            df = pd.read_excel(uploaded_file)

        df.columns = [c.strip() for c in df.columns]
        SEL_COUNTRY = "COUNTRY"
        SEL_TIME = "ALARM TIMESTAMP"

        if SEL_COUNTRY not in df.columns or SEL_TIME not in df.columns:
            st.error("Missing required columns!")
            st.stop()

        # Zeit konvertieren
        df[SEL_TIME] = pd.to_datetime(df[SEL_TIME], errors='coerce')
        df = df.dropna(subset=[SEL_TIME]).sort_values(by=SEL_TIME)

        # ---------------------------------------------------------
        # SECTION 1: QUICK SUMMARY & SETTINGS
        # ---------------------------------------------------------
        st.header("1. Quick Summary")
        
        # Einstellungen (Häkchen) ganz oben für globale Wirkung
        with st.expander("⚙️ Global Display Settings", expanded=True):
            show_full_time = st.checkbox("Force exact timestamps (DD.MM.YYYY HH:MM:SS) in all tables and exports", 
                                         value=True)

        m1, m2 = st.columns(2)
        m1.metric("Total Alarms", len(df))
        m2.metric("Countries Affected", df[SEL_COUNTRY].nunique())

        st.divider()
        col_chart, col_stat = st.columns([2, 1])
        
        # Statistik berechnen: Wir fügen "First Occurrence" und "Last Occurrence" hinzu
        stats_df = df.groupby(SEL_COUNTRY)[SEL_TIME].agg(['count', 'min', 'max']).reset_index()
        stats_df.columns = [SEL_COUNTRY, 'Alarms', 'First Alarm', 'Last Alarm']
        stats_df = stats_df.sort_values(by='Alarms', ascending=False)
        
        with col_chart:
            fig_pie = px.pie(stats_df, values='Alarms', names=SEL_COUNTRY, hole=0.5, title="Distribution")
            st.plotly_chart(fig_pie, use_container_width=True)
            
        with col_stat:
            st.write("### Statistics per Country")
            display_stats = stats_df.copy()
            
            # Hier greift das Häkchen für die Statistik-Tabelle!
            if show_full_time:
                display_stats['First Alarm'] = display_stats['First Alarm'].dt.strftime('%d.%m.%Y %H:%M:%S')
                display_stats['Last Alarm'] = display_stats['Last Alarm'].dt.strftime('%d.%m.%Y %H:%M:%S')
            
            st.dataframe(display_stats, use_container_width=True, hide_index=True)

        # ---------------------------------------------------------
        # SECTION 2: TIMELINE
        # ---------------------------------------------------------
        st.divider()
        st.header("2. Timeline Analysis")
        # (Hier bleibt dein bisheriger Code für die Timeline-Filterung...)
        filter_type = st.radio("Filter View by:", ["Country"], horizontal=True) # Vereinfacht für Beispiel
        items = sorted(df[SEL_COUNTRY].unique().tolist())
        selected_items = st.multiselect("Select Countries:", items, default=items)
        df_filtered = df[df[SEL_COUNTRY].isin(selected_items)].copy()
        
        # Chart
        fig_line = px.line(df_filtered, x=SEL_TIME, color=SEL_COUNTRY, title="Trends")
        st.plotly_chart(fig_line, use_container_width=True)

        # ---------------------------------------------------------
        # SECTION 3: DEEP DIVE & EXPORT
        # ---------------------------------------------------------
        st.divider()
        with st.expander("🔍 Deep Dive & Export"):
            df_final = df_filtered.copy()
            if show_full_time:
                df_final[SEL_TIME] = df_final[SEL_TIME].dt.strftime('%d.%m.%Y %H:%M:%S')
            
            st.dataframe(df_final, use_container_width=True, hide_index=True)
            
            # Export Buttons
            out_xlsx = BytesIO()
            with pd.ExcelWriter(out_xlsx, engine='openpyxl') as writer:
                display_stats.to_excel(writer, index=False, sheet_name='Summary')
                df_final.to_excel(writer, index=False, sheet_name='Details')
            st.download_button("📥 Download Excel", data=out_xlsx.getvalue(), file_name="report.xlsx")

    except Exception as e:
        st.error(f"Error: {e}")
