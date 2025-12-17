import streamlit as st
import simpy
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

# 1. NASTAVENIE STRÁNKY (Musí byť ako prvý príkaz Streamlitu)
st.set_page_config(page_title="Optimalizácia Logistiky", layout="wide")

# 2. BOČNÝ PANEL (SIDEBAR) - Tu sme presunuli ovládanie
with st.sidebar:
    st.header("⚙️ Nastavenia Simulácie")
    num_ramps = st.slider("Počet obslužných rámp", 1, 10, 3)
    arrival_rate = st.slider("Intenzita príchodov (vozidlá/h)", 5, 100, 20)
    avg_service_time = st.slider("Priemerný čas obsluhy (min)", 5, 60, 15)
    sim_time = 480  # 8-hodinová zmena v minútach
    
    st.info("Upravte parametre a sledovať zmeny v reálnom čase.")

# 3. HLAVNÁ PLOCHA
st.title("🚛 Inteligentný Optimalizátor Logistického Uzla")
st.markdown("Simulácia vyťaženosti rámp a čakacích dôb v reálnom čase.")

# --- LOGIKA SIMULÁCIE (SimPy) ---
def truck(env, name, repair_shop, wait_times, service_times):
    arrival_time = env.now
    with repair_shop.request() as request:
        yield request
        wait_time = env.now - arrival_time
        wait_times.append(wait_time)
        
        service_duration = np.random.exponential(avg_service_time)
        service_times.append(service_duration)
        yield env.timeout(service_duration)

def setup(env, num_ramps, arrival_rate, wait_times, service_times):
    repair_shop = simpy.Resource(env, capacity=num_ramps)
    i = 0
    while True:
        yield env.timeout(np.random.exponential(60.0 / arrival_rate))
        i += 1
        env.process(truck(env, f'Truck {i}', repair_shop, wait_times, service_times))

wait_times = []
service_times = []
env = simpy.Environment()
env.process(setup(env, num_ramps, arrival_rate, wait_times, service_times))
env.run(until=sim_time)

# --- VÝSLEDKY A METRIKY ---
if wait_times:
    avg_wait = np.mean(wait_times)
    max_wait = np.max(wait_times)
    utilization = (np.sum(service_times) / (num_ramps * sim_time)) * 100

    # Zobrazenie veľkých ukazovateľov (Metriky)
    col1, col2, col3 = st.columns(3)
    col1.metric("Priemerné čakanie", f"{avg_wait:.1f} min", delta_color="inverse")
    col2.metric("Max. čakacia doba", f"{max_wait:.1f} min", delta_color="inverse")
    col3.metric("Využitie rámp", f"{min(utilization, 100.0):.1f} %")

    st.divider()

    # --- GRAFY ---
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("📊 Distribúcia čakacích dôb")
        fig, ax = plt.subplots()
        ax.hist(wait_times, bins=15, color='skyblue', edgecolor='black')
        ax.set_xlabel("Čas (min)")
        ax.set_ylabel("Počet vozidiel")
        st.pyplot(fig)

    with c2:
        st.subheader("📈 Analýza dát")
        df = pd.DataFrame({"Čas čakania": wait_times})
        st.dataframe(df, use_container_width=True)
        
        # Tlačidlo na stiahnutie dát
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Stiahnuť výsledky (CSV)", data=csv, file_name="simulacia_data.csv")
else:
    st.warning("Simulácia neprebehla, skúste zmeniť parametre.")
