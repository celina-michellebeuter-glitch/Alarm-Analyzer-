import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO
from fpdf import FPDF

# 1. Page Configuration
st.set_page_config(page_title="Alarm Analyzer Pro", layout="wide")

st.title("Alarm Analysis Dashboard")

# Hilfsfunktion für den PDF-Export (Inklusive Uhrzeiten)
def create_pdf(df_summary, df_details):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Alarm Analysis Executive Report", ln=True, align='C')
    pdf.ln(10)
    
    # Sektion: Summary
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "1. Summary by Country", ln=True)
    pdf.set_font("Arial", size=10)
    for i in range(len(df_summary)):
        line = f"{df_summary.iloc[i, 0]}: {df_summary.iloc[i, 1]} Alarms ({df_summary.iloc[i, 2]}%)"
        pdf.cell(0, 8, line, ln=True)
    
    pdf.ln(10)
    # Sektion: Details Snippet mit Uhrzeit
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "2. Detailed Data Snippet (Timestamp incl.)", ln=True)
    pdf.set_font("Arial", size=7)
    
    # Header für Snippet
    cols = ["TIMESTAMP", "COUNTRY", "REGION"]
    pdf.cell(0, 8, " | ".join(cols), ln=True, border=1)
    
    for i in range(min(len(df_details), 40)):
        # Zeitstempel formatiert für PDF
        ts = df_details.iloc[i]["ALARM TIMESTAMP"].strftime('%d.%m.%Y %H:%M:%S')
        country = str(df_details.iloc[i]["COUNTRY"])
        region = str(df_details.iloc[i].get("REGION", "N/A"))
        row_str = f"{ts} | {country} | {region}"
        pdf.cell(0, 7, row_str, ln=True, border=1)
        
    return pdf.output(dest='S').encode('latin-1')

# 2. File Upload
uploaded_file = st.file_uploader("Upload your CSV or Excel file", type=["csv", "xlsx"])

if uploaded_file is not None:
    try:
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
            st.error("Missing required columns: 'COUNTRY' or 'ALARM TIMESTAMP'!")
            st.stop()

        # Konvertierung zu Datetime (Wichtig für den Export mit Uhrzeit)
        df[SEL_TIME] = pd.to_datetime(df[SEL_TIME], errors='coerce')
        df = df.dropna(subset=[SEL_TIME]).sort_values(by=SEL_TIME)

        # Color Mapping
        unique_countries = sorted(df[SEL_COUNTRY].unique().tolist())
        color_palette = px.colors.qualitative.Prism + px.colors.qualitative.Safe
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
        stats_full = df[SEL_COUNTRY].value_counts().reset_index()
        stats_full.columns = [SEL_COUNTRY, 'Count']
        stats_full['Percentage'] = (stats_full['Count'] / stats_full['Count'].sum() * 100).round(2)
        
        with col_chart:
            fig_pie = px.pie(stats_full, values='Count', names=SEL_COUNTRY, hole=0.5, 
                             title="Overall Distribution", color=SEL_COUNTRY, color_discrete_map=color_map)
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_pie, use_container_width=True)
        with col_stat:
            st.write("### Statistics Table")
            display_stats = stats_full.copy()
            display_stats['Percentage'] = display_stats['Percentage'].astype(str) + " %"
            st.dataframe(display_stats, use_container_width=True, hide_index=True)

        # ---------------------------------------------------------
        # SECTION 2: TIMELINE ANALYSIS
        # ---------------------------------------------------------
        st.divider()
        st.header("2. Timeline Analysis")

        t_col1, t_col2 = st.columns([1, 2])
        with t_col1:
            filter_type = st.radio("Filter View by:", ["Country", "Region"], horizontal=True)
        with t_col2:
            base_col = SEL_COUNTRY if filter_type == "Country" else (SEL_REGION if SEL_REGION in df.columns else SEL_COUNTRY)
            items = sorted(df[base_col].unique().tolist())
            selected_items = st.multiselect(f"Select {filter_type}s:", items, default=items)
            
        df_filtered = df[df[base_col].isin(selected_items)].copy()

        c1, c2 = st.columns(2)
        with c1:
            time_view = st.radio("Group by:", ["Exact Time", "Day", "Week", "Month"], horizontal=True, index=0)
        with c2:
            extra_color = st.checkbox("Color by different category?")
            color_target = base_col
            if extra_color:
                color_target = st.selectbox("Choose Category:", [c for c in df.columns if c != SEL_TIME and c != base_col])

        # Grouping
        df_timeline = df_filtered.copy()
        if time_view == "Day": df_timeline['Time Period'] = df_timeline[SEL_TIME].dt.date
        elif time_view == "Week": df_timeline['Time Period'] = df_timeline[SEL_TIME].dt.to_period('W').apply(lambda r: r.start_time)
        elif time_view == "Month": df_timeline['Time Period'] = df_timeline[SEL_TIME].dt.to_period('M').apply(lambda r: r.start_time)
        else: df_timeline['Time Period'] = df_timeline[SEL_TIME]

        group_cols = ['Time Period', base_col]
        if extra_color: group_cols.append(color_target)
        timeline_data = df_timeline.groupby(group_cols).size().reset_index(name='Alarms')
        
        fig_line = px.line(timeline_data, x='Time Period', y='Alarms', color=color_target, markers=True,
                           color_discrete_map=color_map if color_target == SEL_COUNTRY else None,
                           custom_data=[base_col] if extra_color else None)

        fig_line.update_traces(hovertemplate="<b>%{fullData.name}</b><br>Time: %{x|%d.%m.%Y %H:%M:%S}<br>Alarms: %{y}<extra></extra>", marker=dict(size=8))
        fig_line.update_xaxes(rangeslider_visible=True, tickformat="%d.%m.\n%H:%M")
        st.plotly_chart(fig_line, use_container_width=True)

        # ---------------------------------------------------------
        # SECTION 3: DEEP DIVE & EXPORT WITH TIME
        # ---------------------------------------------------------
        st.divider()
        with st.expander("Uploaded Data & Download Informations"):
            st.subheader("Final Data Selection (Sorted by Time)")
            
            # Für die Anzeige formatieren wir die Zeit schön
            df_display = df_filtered.sort_values(by=SEL_TIME, ascending=False).copy()
            st.dataframe(df_display, use_container_width=True, hide_index=True)
            
            st.write("### Download Full Report (Including Precise Timestamps)")
            dl1, dl2, dl3 = st.columns(3)
            
            # EXCEL Export (Mit Zeit-Formatierung)
            out_xlsx = BytesIO()
            # Wir sorgen dafür, dass Excel die Spalte als Datum/Zeit erkennt
            with pd.ExcelWriter(out_xlsx, engine='openpyxl') as writer:
                stats_full.to_excel(writer, index=False, sheet_name='Summary')
                # Detail-Daten exportieren
                df_filtered.to_excel(writer, index=False, sheet_name='Detailed Data')
                
            dl1.download_button("📥 Excel (Summary + All Details)", data=out_xlsx.getvalue(), file_name="full_report_with_time.xlsx")
            
            # CSV Export (Zeitstempel als String, damit Excel ihn nicht automatisch kürzt)
            df_csv = df_filtered.copy()
            df_csv[SEL_TIME] = df_csv[SEL_TIME].dt.strftime('%Y-%m-%d %H:%M:%S')
            csv_data = df_csv.to_csv(index=False).encode('utf-8')
            dl2.download_button("📥 CSV (Detailed Times)", data=csv_data, file_name="details_with_time.csv", mime="text/csv")
            
            # PDF Export
            try:
                pdf_bytes = create_pdf(stats_full, df_filtered)
                dl3.download_button("📥 PDF (Summary Report)", data=pdf_bytes, file_name="report_summary.pdf", mime="application/pdf")
            except:
                dl3.error("PDF Export Error")

    except Exception as e:
        st.error(f"Error: {e}")
else:
    st.info("Please upload a file to start.")
