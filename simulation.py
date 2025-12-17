import streamlit as st
import simpy
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

# --- KONFIGURÁCIA ---
st.set_page_config(page_title="Logistics Optimizer PRO", layout="wide", initial_sidebar_state="expanded")

# --- ŠTÝL (CSS) pre lepšie farby ---
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True) # <--- TOTO JE SPRÁVNE

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2312/2312732.png", width=100) # Ikona kamiónu
    st.title("Parametre Uzla")
    st.divider()
    
    num_ramps = st.number_input("Počet rámp", 1, 20, 3)
    arrival_rate = st.slider("Príchody (vozidlá/hod)", 5, 120, 25)
    avg_service_time = st.slider("Čas obsluhy (min)", 5, 90, 20)
    
    st.divider()
    st.success("Tento model simuluje náhodné príchody vozidiel (Poissonov proces) a exponenciálnu dĺžku obsluhy.")

# --- SIMULAČNÝ ENGINE ---
def run_simulation(num_ramps, arrival_rate, avg_service_time):
    env = simpy.Environment()
    repair_shop = simpy.Resource(env, capacity=num_ramps)
    wait_times = []
    service_times = []

    def truck(env, repair_shop):
        arrival = env.now
        with repair_shop.request() as request:
            yield request
            wait_times.append(env.now - arrival)
            duration = np.random.exponential(avg_service_time)
            service_times.append(duration)
            yield env.timeout(duration)

    def setup(env):
        while True:
            yield env.timeout(np.random.exponential(60.0 / arrival_rate))
            env.process(truck(env, repair_shop))

    env.process(setup(env))
    env.run(until=480) # 8 hodín
    return wait_times, service_times

# --- VÝPOČET A ZOBRAZENIE ---
wait_times, service_times = run_simulation(num_ramps, arrival_rate, avg_service_time)

# HLAVNÝ OBSAH
st.title("📊 Logistics Terminal Optimizer")
st.subheader("Optimalizácia kapacity a minimalizácia úzkych hrdiel")

# Karty pre lepšiu navigáciu
tab1, tab2, tab3 = st.tabs(["🎯 Dashboard", "🔍 Detailná Analýza", "📁 Export Dát"])

with tab1:
    if wait_times:
        avg_wait = np.mean(wait_times)
        utilization = (np.sum(service_times) / (num_ramps * 480)) * 100
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Priemerné čakanie", f"{avg_wait:.1f} min", 
                  delta="- OK" if avg_wait < 15 else "+ KRITICKÉ", delta_color="inverse")
        c2.metric("Využitie kapacity", f"{min(utilization, 100):.1f} %")
        c3.metric("Odbavené vozidlá", len(wait_times))
        
        st.divider()
        
        # Graf vyťaženia počas dňa
        st.subheader("Priebeh fronty v čase")
        chart_data = pd.DataFrame({"Čakacia doba": wait_times})
        st.area_chart(chart_data, use_container_width=True)

with tab2:
    col_left, col_right = st.columns(2)
    with col_left:
        st.write("### Rozdelenie čakacích dôb")
        fig, ax = plt.subplots()
        ax.hist(wait_times, bins=20, color='#2e7d32', edgecolor='white')
        ax.set_title("Histogram (min)")
        st.pyplot(fig)
    with col_right:
        st.write("### Štatistický prehľad")
        st.write(pd.Series(wait_times).describe())

with tab3:
    st.write("### Stiahnuť kompletný report")
    df_export = pd.DataFrame({"Vozidlo_ID": range(1, len(wait_times)+1), "Čakanie_min": wait_times})
    st.dataframe(df_export, use_container_width=True)
    st.download_button("Exportovať do Excelu (CSV)", df_export.to_csv().encode('utf-8'), "report.csv")

