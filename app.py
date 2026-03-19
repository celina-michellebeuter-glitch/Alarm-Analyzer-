import streamlit as st
import pandas as pd
import plotly.express as px

# Seiteneinstellungen
st.set_page_config(page_title="Alarm Analyse Tool", layout="wide")

st.title("🛡️ Geräte- & Alarm-Auswertung")
st.info("Lade deine Excel- oder CSV-Datei hoch, um die Verteilung nach Ländern und Zeiten zu sehen.")

# Datei Upload
uploaded_file = st.file_uploader("Datei hier hochladen", type=["csv", "xlsx"])

if uploaded_file is not None:
    try:
        # Daten einlesen
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        # Spaltennamen basierend auf deinem Screenshot
        col_country = "COUNTRY"
        col_time = "ALARM TIMESTAMP"
        col_system = "SYSTEM CLASS"

        # Check, ob Spalten existieren
        if col_country in df.columns and col_time in df.columns:
            
            # Zeitspalte umwandeln
            df[col_time] = pd.to_datetime(df[col_time], errors='coerce')
            
            # --- TEIL 1: GERÄTE PRO LAND ---
            st.header("1. Betroffene Geräte pro Land")
            
            # Gruppierung: Wie viele Einträge pro Land
            country_stats = df[col_country].value_counts().reset_index()
            country_stats.columns = ['Land', 'Anzahl Alarme']
            
            # Prozentberechnung
            total_alarms = country_stats['Anzahl Alarme'].sum()
            country_stats['Anteil in %'] = ((country_stats['Anzahl Alarme'] / total_alarms) * 100).round(2)
            
            col_left, col_right = st.columns([1, 1])
            
            with col_left:
                st.subheader("Tabellarische Übersicht")
                st.dataframe(country_stats, use_container_width=True)
                
            with col_right:
                fig_pie = px.pie(country_stats, values='Anzahl Alarme', names='Land', 
                                 title="Prozentuale Verteilung",
                                 hole=0.4)
                st.plotly_chart(fig_pie, use_container_width=True)

            # --- TEIL 2: ZEITLICHE ANALYSE ---
            st.divider()
            st.header("2. Zeitliche Analyse der Alarme")
            
            # Wir extrahieren das Datum und die Stunde für eine bessere Übersicht
            df['Datum'] = df[col_time].dt.date
            
            # Zeitverlauf Plot
            timeline = df.groupby(['Datum', col_country]).size().reset_index(name='Anzahl')
            
            fig_line = px.line(timeline, x='Datum', y='Anzahl', color=col_country,
                               markers=True, title="Wann wurde in welchem Land Alarm ausgelöst?")
            st.plotly_chart(fig_line, use_container_width=True)
            
            # Optionale Detail-Tabelle
            with st.expander("Rohdaten anzeigen"):
                st.write(df[[col_country, col_system, col_time]])

        else:
            st.error(f"Spalten nicht gefunden. Erwartet werden '{col_country}' und '{col_time}'.")
            st.write("Vorhandene Spalten:", list(df.columns))

    except Exception as e:
        st.error(f"Fehler bei der Verarbeitung: {e}")

else:
    st.write("---")
    st.write("💡 **Tipp:** Deine Datei sollte Spalten wie `COUNTRY` und `ALARM TIMESTAMP` enthalten, damit die Analyse funktioniert.")