import streamlit as st
import pandas as pd
import numpy as np

# 1. PLATFORM & PHONE OPTIMIZATION CONFIG
st.set_page_config(
    page_title="Ultimate Footy Ensemble Engine",
    page_icon="⚽",
    layout="centered", # Better formatting for single-column mobile view
    initial_sidebar_state="collapsed"
)

# Custom responsive CSS for Mobile vs Windows styling
st.markdown("""
    <style>
    .stSlider [data-baseweb="slider"] { margin-bottom: 20px; }
    @media (max-width: 640px) {
        .main .block-container { padding: 10px; }
        h1 { font-size: 24px !important; }
    }
    </style>
""", unsafe_with_html=True)

st.title("⚽ Ultimate Football Ensemble Predictor")
st.write("Cross-platform engine for Domestic Leagues and UEFA Tournaments.")

# 2. COMPETITION ROUTING AND FREE STATS SCRAPER
tournament_urls = {
    "🏴󠁧󠁢󠁥󠁮󠁧󠁿 English Premier League": "https://fbref.com",
    "🏆 UEFA Champions League": "https://fbref.com",
    "🇪🇺 UEFA Europa League": "https://fbref.com",
    "🌱 UEFA Conference League": "https://fbref.com"
}

selected_tournament = st.selectbox("🌐 Choose Tournament / League", list(tournament_urls.keys()))

@st.cache_data(ttl=3600)
def fetch_tournament_data(url):
    try:
        tables = pd.read_html(url)
        # Look for the primary standings table containing standard and advanced stats
        for table in tables:
            cols = [c[-1] if isinstance(c, tuple) else c for c in table.columns]
            table.columns = cols
            if 'Squad' in table.columns and ('xG' in table.columns or 'GF' in table.columns):
                # Clean up if some values are missing metrics
                if 'xG' not in table.columns: table['xG'] = table['GF']
                if 'xGA' not in table.columns: table['xGA'] = table['GA']
                return table[['Squad', 'MP', 'W', 'D', 'L', 'GF', 'GA', 'xG', 'xGA']].dropna()
        return None
    except Exception as e:
        return None

df_stats = fetch_tournament_data(tournament_urls[selected_tournament])

# 3. DYNAMIC METRIC MANAGER (UPDATABLE SETTINGS)
if 'custom_metrics' not in st.session_state:
    # Pre-load with core foundational metrics we discussed
    st.session_state.custom_metrics = ["Open-Play xG Performance", "Pressing Intensity (PPDA)", "Squad Lineup Strength / Injuries"]

st.sidebar.header("🛠️ Metric Configurator")
st.sidebar.write("Add your own new custom metrics to evaluate live matches below:")
new_metric_input = st.sidebar.text_input("New Metric Name (e.g., Field Tilt %)")
if st.sidebar.button("➕ Add Metric Into System"):
    if new_metric_input and new_metric_input not in st.session_state.custom_metrics:
        st.session_state.custom_metrics.append(new_metric_input)
        st.sidebar.success(f"Added: {new_metric_input}")

if st.sidebar.button("🧹 Reset to Defaults"):
    st.session_state.custom_metrics = ["Open-Play xG Performance", "Pressing Intensity (PPDA)", "Squad Lineup Strength / Injuries"]

# Main Execution Flow
if df_stats is not None:
    teams = sorted(df_stats['Squad'].unique().tolist())
    
    # Responsive grid layout
    col1, col2 = st.columns(2)
    with col1:
        home_team = st.selectbox("🏠 Home Team", teams, index=0)
    with col2:
        away_team = st.selectbox("🚀 Away Team", teams, index=1 if len(teams) > 1 else 0)

    # Calculate underlying baseline metrics per 90 mins played
    h_row = df_stats[df_stats['Squad'] == home_team].iloc[0]
    a_row = df_stats[df_stats['Squad'] == away_team].iloc[0]

    h_mp = float(h_row['MP']) if float(h_row['MP']) > 0 else 1
    a_mp = float(a_row['MP']) if float(a_row['MP']) > 0 else 1

    h_xg = float(h_row['xG']) / h_mp
    h_xga = float(h_row['xGA']) / h_mp
    a_xg = float(a_row['xG']) / a_mp
    a_xga = float(a_row['xGA']) / a_mp

    st.info(f"📊 **Auto-Scraped Baselines (Per Game):**\n"
            f"• {home_team} Attacking: {h_xg:.2f} | Defensive: {h_xga:.2f}\n"
            f"• {away_team} Attacking: {a_xg:.2f} | Defensive: {a_xga:.2f}")

    # 4. ITERATE & GENERATE SLIDERS FOR UPDATED CUSTOM METRICS
    st.subheader("📝 Rate Your Custom Metrics (Scale 0-10)")
    st.caption("5.0 represents a perfectly balanced league matchup baseline.")
    
    home_ratings = []
    away_ratings = []
    
    for metric in st.session_state.custom_metrics:
        st.markdown(f"**Metric: {metric}**")
        h_val = st.slider(f"🏠 {home_team} Score", 0.0, 10.0, 5.0, 0.5, key=f"h_{metric}")
        a_val = st.slider(f"🚀 {away_team} Score", 0.0, 10.0, 5.0, 0.5, key=f"a_{metric}")
        home_ratings.append(h_val)
        away_ratings.append(a_val)
        st.markdown("---")

    # Matchday Situational Elements
    st.subheader("🌍 Matchday Context Modifiers")
    rest_fatigue = st.slider("⚖️ Net Fatigue / Rest Advantage (5.0 = Equal)", 0.0, 10.0, 5.0, 0.5)
    market_sentiment = st.slider("📉 Smart Money Late Odds Market Shift", 0.0, 10.0, 5.0, 0.5)

    # Compute overall relative score averages
    h_mod = np.mean(home_ratings) / 5.0 if home_ratings else 1.0
    a_mod = np.mean(away_ratings) / 5.0 if away_ratings else 1.0
    fatigue_mod = rest_fatigue / 5.0
    market_mod = market_sentiment / 5.0

    # 5. FOUR-FORMULA PROCESSING MATRIX
    base_h = 1.35 * (h_xg / 1.25)
    base_a = 1.15 * (a_xg / 1.25)

    # Formula 1: Multiplicative Proportional
    f1_h = base_h * h_mod * (1 / (max(0.1, a_xga) * 0.8))
    f1_a = base_a * a_mod * (1 / (max(0.1, h_xga) * 0.8)) * fatigue_mod

    # Formula 2: Log-Linear Regression Proxy
    f2_h = np.exp(np.log(max(0.1, base_h)) + (h_mod - 1.0))
    f2_a = np.exp(np.log(max(0.1, base_a)) + (a_mod - 1.0)) * fatigue_mod

    # Formula 3: Elo Adjustment Curve
    f3_h = max(0.1, base_h + (h_mod - a_mod) * 0.4)
    f3_a = max(0.1, base_a + (a_mod - h_mod) * 0.4 * fatigue_mod)

    # Formula 4: Tactical Low-Block
    f4_h = base_h * 0.85 if h_mod < a_mod else base_h * 1.1
    f4_a = base_a * 0.80 if fatigue_mod < 1.0 else base_a * 1.0

    # Blended Average Projection
    final_home_xg = np.mean([f1_h, f2_h, f3_h, f4_h]) * market_mod
    final_away_xg = np.mean([f1_a, f2_a, f3_a, f4_a])

    # 6. ENSEMBLE OUTPUT GENERATION
    st.subheader("🎯 Blended Prediction Target Outcomes")
    
    mcol1, mcol2 = st.columns(2)
    with mcol1:
        st.metric(label=f"🏠 {home_team} Projected xG", value=f"{final_home_xg:.2f}")
    with mcol2:
        st.metric(label=f"🚀 {away_team} Projected xG", value=f"{final_away_xg:.2f}")

    # Monte Carlo Engine (10,000 matches simulated live)
    simulations = 10000
    h_sim_goals = np.random.poisson(max(0, final_home_xg), simulations)
    a_sim_goals = np.random.poisson(max(0, final_away_xg), simulations)

    home_wins = np.sum(h_sim_goals > a_sim_goals) / simulations * 100
    away_wins = np.sum(a_sim_goals > h_sim_goals) / simulations * 100
    draws = np.sum(h_sim_goals == a_sim_goals) / simulations * 100

    st.markdown("### 📈 Probabilities")
    st.write(f"**🏠 {home_team} Win:** `{home_wins:.1f}%`")
    st.write(f"**🤝 Draw:** `{draws:.1f}%`")
    st.write(f"**🚀 {away_team} Win:** `{away_wins:.1f}%`")

    # Generate Top Exact Score Probability Matrix
    scorelines = {}
    for h, a in zip(h_sim_goals, a_sim_goals):
        combo = f"{h}-{a}"
        scorelines[combo] = scorelines.get(combo, 0) + 1
        
    top_scoreline = max(scorelines, key=scorelines.get)
    top_scoreline_pct = (scorelines[top_scoreline] / simulations) * 100
    
    st.success(f"🔮 **Most Probable Result:** {top_scoreline} ({top_scoreline_pct:.1f}% Likelihood)")
else:
    st.error("Data tracking connection failed. Check if FBref is blocked or verify your network link.")
