import simpy
import random
import statistics
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

# --- 1. PARAMETRE SIMULÁCIE (KONŠTANTY) ---

SIM_DURATION = 5000         # Simulácia 5000 minút
COST_PER_HOUR_WAITING = 60  # Náklady na čakanie (1 €/min)
COST_PER_HOUR_SERVER = 20   # Náklady na 1 obsluhujúceho pracovníka (0.33 €/min)
RANDOM_SEED = 42

# --- 2. MODEL SYSTÉMU (Opravená manipulácia s dátami) ---

# Funkcia sa stáva generátorom, ktorý zbiera dáta lokálne v danej simulácii
def client(env, servers, inter_arrival_time, service_time, all_wait_times):
    """Proces klienta/auta v systéme."""
    
    arrival_time = env.now 
    
    with servers.request() as req:
        yield req
        
        wait_time = env.now - arrival_time
        all_wait_times.append(wait_time) # Pridávame do zoznamu, ktorý nám prišiel ako argument
        
        # Realistickejší čas obsluhy: Normálne rozdelenie (M/G/s)
        service_duration = max(0, np.random.normal(service_time, 2))
        yield env.timeout(service_duration) 

def setup(env, num_servers, inter_arrival_time, service_time, all_wait_times):
    """Generátor príchodov klientov."""
    servers = simpy.Resource(env, capacity=num_servers) 
    
    i = 0
    while True:
        i += 1
        # Odovzdávame all_wait_times ako argument do klienta
        env.process(client(env, servers, inter_arrival_time, service_time, all_wait_times)) 
        
        # Príchody sú stále Exponenciálne (M/G/s model)
        yield env.timeout(random.expovariate(1.0 / inter_arrival_time)) 

# --- 3. Funkcia pre Kvantifikáciu Nákladov ---

def calculate_costs(num_servers, total_wait_time, duration):
    """Kvantifikuje náklady na čakanie a náklady na obsluhu."""
    
    waiting_cost = total_wait_time * (COST_PER_HOUR_WAITING / 60)
    server_cost = num_servers * duration * (COST_PER_HOUR_SERVER / 60)
    total_cost = waiting_cost + server_cost
    
    return waiting_cost, server_cost, total_cost

# --- 4. Funkcia pre Spustenie Simulácie ---

# Používame st.cache_data, aby Streamlit nespúšťal simuláciu pri každej zmene UI, ale len pri zmene vstupov
@st.cache_data 
def run_simulation(num_servers, inter_arrival_time, service_time, duration):
    """Spustí simulačné prostredie a vráti výsledky."""
    
    random.seed(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)
    
    WAIT_TIMES_LOCAL = [] # Lokálny zoznam pre konkrétnu simuláciu
    
    env = simpy.Environment() 
    # Odovzdávame lokálny zoznam do setup funkcie
    env.process(setup(env, num_servers, inter_arrival_time, service_time, WAIT_TIMES_LOCAL)) 
    env.run(until=duration) 
    
    if not WAIT_TIMES_LOCAL:
        return None, None, None, None, None

    avg_wait = statistics.mean(WAIT_TIMES_LOCAL)
    total_wait_time = sum(WAIT_TIMES_LOCAL) # Súčet všetkých časov
    
    # Kvantifikácia nákladov
    waiting_cost, server_cost, total_cost = calculate_costs(num_servers, total_wait_time, duration)
    
    return avg_wait, waiting_cost, server_cost, total_cost, WAIT_TIMES_LOCAL

def find_optimal_servers(inter_arrival_time, service_time, min_servers=1, max_servers=5):
    """Iteruje cez rozsah serverov a nachádza optimálne riešenie."""
    
    results = []
    
    for num_servers in range(min_servers, max_servers + 1):
        
        avg_wait, waiting_cost, server_cost, total_cost, _ = run_simulation(
            num_servers, inter_arrival_time, service_time, SIM_DURATION
        )

        if total_cost is not None:
            results.append({
                'Rampy (s)': num_servers,
                'Priemerná Čakacia Doba (min)': avg_wait,
                'Náklady na Čakanie (€)': waiting_cost,
                'Náklady na Obsluhu (€)': server_cost,
                'CELKOVÉ NÁKLADY (€)': total_cost
            })
    
    return pd.DataFrame(results)

# --- 5. STREAMLIT APLIKÁCIA ---

if __name__ == '__main__':
    st.set_page_config(layout="wide")
    st.title("🚚 Optimalizátor Logistických Rámp / Obsluhy")
    st.markdown("### Automatická optimalizácia pre Vaše procesy")

    # --- SIDEBAR PRE VSTUPNÉ PARAMETRE ---

    st.sidebar.header("Parametre Vášho Systému")

    # Interaktívne vstupy od užívateľa
    inter_arrival_time = st.sidebar.slider(
        '1. Priemerný čas medzi príchodmi (min)', 
        min_value=1.0, max_value=20.0, value=10.0, step=0.5
    )

    service_time = st.sidebar.slider(
        '2. Priemerný čas potrebný na obsluhu (min)', 
        min_value=1.0, max_value=15.0, value=8.0, step=0.5
    )
    
    num_servers_detail = st.sidebar.slider(
        '3. Detailné dáta pre (počet rámp):', 
        min_value=1, max_value=5, value=2, step=1
    )


    # --- HLAVNÝ VÝSTUP (Automatické hľadanie Optima) ---

    comparison_df = find_optimal_servers(inter_arrival_time, service_time, min_servers=1, max_servers=5)

    if not comparison_df.empty:
        
        # Nájdenie optima
        optimal_row = comparison_df.loc[comparison_df['CELKOVÉ NÁKLADY (€)'].idxmin()]
        optimal_servers = int(optimal_row['Rampy (s)'])
        optimal_cost = optimal_row['CELKOVÉ NÁKLADY (€)']
        
        # 1. Zobrazenie optimálneho riešenia
        st.success(f"""
            **OPTIMUM BOLO NÁJDENÉ:**
            Najnižšie celkové náklady ({optimal_cost:.2f} € za {SIM_DURATION} min) dosiahnete pri **{optimal_servers}** rampách.
        """)
        
        # 2. Vizuálne porovnanie
        st.subheader("Porovnanie Scenárov - Kde Platíte Najmenej?")
        
        comparison_df_viz = comparison_df[['Rampy (s)', 'Náklady na Čakanie (€)', 'Náklady na Obsluhu (€)', 'CELKOVÉ NÁKLADY (€)']]
        
        st.bar_chart(
            comparison_df_viz.set_index('Rampy (s)')[['Náklady na Čakanie (€)', 'Náklady na Obsluhu (€)']]
        )
        
        # 3. Detailná tabuľka
        st.subheader("Detailná Analýza Výsledkov")
        
        comparison_df_display = comparison_df.style.highlight_min(subset=['CELKOVÉ NÁKLADY (€)'], axis=0, color='lightgreen')
        st.dataframe(comparison_df_display, use_container_width=True)

        # 4. Vizualizácia pre detailne vybraný počet rámp
        st.markdown("---")
        st.subheader(f"Detailná distribúcia čakania pre {num_servers_detail} rámp")
        
        # Spustíme simuláciu len pre konkrétne nastavenie vybrané v sidebar (num_servers_detail)
        avg_wait_detail, total_cost_detail, _, _, wait_times_detail = run_simulation(
            num_servers_detail, inter_arrival_time, service_time, SIM_DURATION
        )

        if wait_times_detail:
            # Kreslenie grafu (Matplotlib)
            fig, ax = plt.subplots(figsize=(10, 5))
            ax.hist(wait_times_detail, bins=20, density=True, alpha=0.7, color='teal', edgecolor='black')
            ax.axvline(avg_wait_detail, color='red', linestyle='dashed', linewidth=2, 
                        label=f'Priemerné čakanie: {avg_wait_detail:.2f} min')
            ax.set_title(f'Histogram čakacích dôb pre {num_servers_detail} rámp')
            ax.set_xlabel('Čas čakania (minúty)')
            ax.legend()
            st.pyplot(fig)

        # 5. CTA (Call To Action - Háčik)
        st.markdown("---")
        st.button("Chcem hĺbkovú optimalizáciu a presnú kalkuláciu úspor")

    else:
        st.error("Žiadny serverový variant nebol stabilný. Skúste zmeniť vstupné parametre (napr. spomaľte príchody alebo skráťte obsluhu).")