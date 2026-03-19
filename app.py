import streamlit as st
import pandas as pd
import plotly.express as px

# Seiteneinstellungen
st.set_page_config(page_title="Alarm Analyse Tool", layout="wide")

st.title("Alarm Analysis")
st.info("Upload your Excel or CSV file. The tool will automatically calculate the distribution and timing.")

# Datei Upload
uploaded_file = st.file_uploader("Upload file here (CSV or Excel)", type=["csv", "xlsx"])

if uploaded_file is not None:
    try:
        # 1. Daten einlesen mit automatischer Formaterkennung
        if uploaded_file.name.endswith('.csv'):
            # sep=None und engine='python' erkennt automatisch Komma oder Semikolon
            df = pd.read_csv(uploaded_file, sep=None, engine='python')
        else:
            df = pd.read_excel(uploaded_file)

        # 2. Spalten-Identifikation (Wir suchen nach COUNTRY und ALARM TIMESTAMP)
        # Wir machen die Suche flexibel, falls Leerzeichen davor/danach sind
        cols = {col.strip().upper(): col for col in df.columns}
        
        col_country = cols.get("COUNTRY")
        col_time = cols.get("ALARM TIMESTAMP")

        if col_country and col_time:
            # Zeitspalte in echtes Datum umwandeln
            df[col_time] = pd.to_datetime(df[col_time], errors='coerce')
            # Zeilen ohne gültiges Datum entfernen
            df = df.dropna(subset=[col_time])
            
            # --- ANALYSE 1: GERÄTE PRO LAND ---
            st.divider()
            st.header("1. Affected devices by country")
            
            # Berechnung der Anzahl und Prozente
            country_stats = df[col_country].value_counts().reset_index()
            country_stats.columns = ['Land', 'Anzahl Alarme']
            
            total_alarms = country_stats['Anzahl Alarme'].sum()
            country_stats['Anteil in %'] = ((country_stats['Anzahl Alarme'] / total_alarms) * 100).round(2)
            
            c1, c2 = st.columns([1, 2])
            with c1:
                st.subheader("Übersichtstabelle")
                # Formatierung für die Prozentanzeige in der Tabelle
                st.dataframe(country_stats.style.format({'Anteil in %': '{:.2f}%'}), use_container_width=True)
                
            with c2:
                fig_pie = px.pie(country_stats, values='Anzahl Alarme', names='Land', 
                                 title="Prozentuale Verteilung der Alarme",
                                 hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
                st.plotly_chart(fig_pie, use_container_width=True)

            # --- ANALYSE 2: ZEITLICHE ANALYSE ---
            st.divider()
            st.header("2. When did the alarms go off?")
            
            # Datum extrahieren für die Grafik (Tag-genau)
            df['Datum'] = df[col_time].dt.date
            timeline = df.groupby(['Datum', col_country]).size().reset_index(name='Alarme')
            
            fig_line = px.line(timeline, x='Datum', y='Alarme', color=col_country,
                               markers=True, title="Time series by country",
                               labels={'Alarme': 'Anzahl Alarme', 'Datum': 'Tag'})
            
            # Grafik schöner machen
            fig_line.update_layout(hovermode="x unified")
            st.plotly_chart(fig_line, use_container_width=True)
            
            # Rohdaten-Check
            with st.expander("Preview of the processed data"):
                st.write(df[[col_country, col_time]].sort_values(by=col_time))

        else:
            st.error("⚠️ Error: The columns ‘COUNTRY’ or ‘ALARM TIMESTAMP’ were not found.")
            st.write("Columns found in your file:", list(df.columns))
            st.info("Please check to make sure the column headers are in the first row of your file.")

    except Exception as e:
        st.error(f"❌ A technical error has occurred: {e}")

else:
    st.write("---")
    st.markdown("### Anleitung:")
    st.write("1.  Export your data as an Excel or CSV file.")
    st.write("2. Make sure that the **‘COUNTRY’** and **‘ALARM TIMESTAMP’** columns are present.")
    st.write("3. Upload the file above.")
