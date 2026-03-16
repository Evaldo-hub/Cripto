import streamlit as st
import pandas as pd
import numpy as np
import ccxt
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import ta # Technical Analysis Library: pip install ta

# Configuração da Página
st.set_page_config(
    page_title="Crypto Quant Scanner v4.2",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilização CSS Moderna para Dashboard Institucional
st.markdown("""
    <style>
    .metric-box {
        background-color: #1E2329;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #2B3139;
        color: white;
    }
    .buy-color { color: #0ECB81; }
    .sell-color { color: #F6465D; }
    </style>
""", unsafe_allow_html=True)

st.title("🤖 Dashboard Analítico Quantitativo Institucional")
st.markdown("Sistema de varredura 4H - Identificação de Padrões e Acumulação Institucional")

# Sidebar
st.sidebar.header("⚙️ Parâmetros do Scanner")
tickers_input = st.sidebar.text_input("Ativos Binance (separados por vírgula)", "BTC/USDT, ETH/USDT, SOL/USDT, AVAX/USDT, INJ/USDT")
timeframe = st.sidebar.selectbox("Timeframe", ["1h", "4h", "1d"], index=1, help="Timeframes da Binance (Recomendado 4h)")
ma_period = st.sidebar.number_input("Período EMA Principal", 10, 200, 56)

@st.cache_data(ttl=300)
def load_data(ticker, interval="4h", limit=200):
    try:
        exchange = ccxt.binance({'enableRateLimit': True})
        bars = exchange.fetch_ohlcv(ticker, timeframe=interval, limit=limit)
        if not bars:
            return None
        df = pd.DataFrame(bars, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
        df['Timestamp'] = pd.to_datetime(df['Timestamp'], unit='ms')
        df.set_index('Timestamp', inplace=True)
        return df
    except Exception as e:
        return None

def apply_indicators(df):
    # RSI
    df['RSI'] = ta.momentum.RSIIndicator(df['Close'], window=14).rsi()
    
    # Stochastic RSI
    stoch_rsi = ta.momentum.StochRSIIndicator(df['Close'], window=14, smooth1=3, smooth2=3)
    df['Stoch_RSI_K'] = stoch_rsi.stochrsi_k() * 100
    df['Stoch_RSI_D'] = stoch_rsi.stochrsi_d() * 100
    
    # MACD
    macd = ta.trend.MACD(df['Close'], window_slow=26, window_fast=12, window_sign=9)
    df['MACD'] = macd.macd()
    df['MACD_Signal'] = macd.macd_signal()
    df['MACD_Hist'] = macd.macd_diff()
    
    # EMA 56
    df['EMA_56'] = ta.trend.EMAIndicator(df['Close'], window=56).ema_indicator()
    
    # Média de Volume (20)
    df['Vol_SMA_20'] = df['Volume'].rolling(window=20).mean()
    
    return df

def calcular_score_sinal(row, current_price):
    score = 0
    sinal = "AGUARDAR"
    motivo = []
    
    # Tendência (20 pts)
    if current_price > row['EMA_56']:
        score += 20
        motivo.append("Preço acima da EMA 56")
    
    # RSI (15 pts)
    if 50 < row['RSI'] < 70:
        score += 15
        motivo.append("RSI em zona de força compradora")
    elif row['RSI'] < 30:
        score += 10 # Sobrevendido
        motivo.append("RSI Sobrevendido")
        
    # MACD (15 pts)
    if row['MACD'] > row['MACD_Signal']:
        score += 15
        motivo.append("MACD Cruzamento Positivo")
        
    # Volume (20 pts)
    if row['Volume'] > row['Vol_SMA_20']:
        score += 20
        motivo.append("Volume acima da média")
        
    # Vol Spike
    if row['Volume'] > (row['Vol_SMA_20'] * 2):
        score += 10
        motivo.append("🔥 VOLUME SPIKE DETECTADO")
        
    if score >= 60:
        sinal = "COMPRA"
    elif score <= 30 and current_price < row['EMA_56']:
        sinal = "VENDA"
        
    return score, sinal, ", ".join(motivo)

tickers = [t.strip() for t in tickers_input.split(',')]

col1, col2, col3 = st.columns(3)

if st.sidebar.button("🚀 Iniciar Análise Global"):
    with st.spinner("Conectando aos provedores de liquidez e analisando dados..."):
        resultados = []
        
        for ticker in tickers:
            df = load_data(ticker, interval=timeframe)
            if df is not None and len(df) > 60:
                df = apply_indicators(df)
                last_row = df.iloc[-1]
                current_price = last_row['Close']
                
                score, sinal, motivo = calcular_score_sinal(last_row, current_price)
                
                resultados.append({
                    "Ativo": ticker.replace("/USDT", ""),
                    "Preço": current_price,
                    "Score": score,
                    "Sinal": sinal,
                    "RSI": last_row['RSI'],
                    "Volume 24h": last_row['Volume'],
                    "Status": "Normal" if score < 70 else "Breakout Provável",
                    "Observação": motivo
                })
        
        if resultados:
            df_res = pd.DataFrame(resultados).sort_values(by="Score", ascending=False)
            
            # Top Metrics
            top_coin = df_res.iloc[0]
            col1.markdown(f"""
            <div class="metric-box">
                <h3 style="margin:0; color:#888;">Top Oportunidade</h3>
                <h2 style="margin:0; color:#0ECB81;">{top_coin['Ativo']}</h2>
                <p style="margin:0;">Score: {top_coin['Score']}/100</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Mostrar Tabela de Scanner
            st.subheader("📊 Resultados do Scanner Ativo")
            
            def map_color(val):
                if val == "COMPRA": return 'background-color: rgba(14, 203, 129, 0.2); color: #0ECB81;'
                if val == "VENDA": return 'background-color: rgba(246, 70, 93, 0.2); color: #F6465D;'
                return ''
                
            st.dataframe(df_res.style.map(map_color, subset=['Sinal']), use_container_width=True)
            
            # Gráfico de Análise Dinâmico
            st.subheader(f"📈 Gráfico Analítico Avançado: {top_coin['Ativo']}")
            
            df_top = load_data(top_coin['Ativo']+"/USDT", interval=timeframe)
            df_top = apply_indicators(df_top)
            df_plot = df_top.tail(100) # Últimas 100 velas
            
            fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                                vertical_spacing=0.05, row_heights=[0.6, 0.2, 0.2])

            # Preço e EMA
            fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'],
                                         low=df_plot['Low'], close=df_plot['Close'], name='Preço'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['EMA_56'], line=dict(color='orange', width=2), name='EMA 56'), row=1, col=1)

            # Volume
            colors = ['#0ECB81' if row['Close'] >= row['Open'] else '#F6465D' for index, row in df_plot.iterrows()]
            fig.add_trace(go.Bar(x=df_plot.index, y=df_plot['Volume'], marker_color=colors, name='Volume'), row=2, col=1)
            fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['Vol_SMA_20'], line=dict(color='yellow', width=1), name='Média Vol'), row=2, col=1)

            # MACD
            colors_macd = ['#0ECB81' if val >= 0 else '#F6465D' for val in df_plot['MACD_Hist']]
            fig.add_trace(go.Bar(x=df_plot.index, y=df_plot['MACD_Hist'], marker_color=colors_macd, name='MACD Hist'), row=3, col=1)
            fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['MACD'], line=dict(color='blue', width=1), name='MACD'), row=3, col=1)
            fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['MACD_Signal'], line=dict(color='orange', width=1), name='Signal'), row=3, col=1)

            fig.update_layout(height=800, plot_bgcolor='#1E2329', paper_bgcolor='#1E2329', 
                              font=dict(color='white'), margin=dict(l=20, r=20, t=20, b=20),
                              xaxis_rangeslider_visible=False)
            fig.update_yaxes(gridcolor='#2B3139')
            fig.update_xaxes(gridcolor='#2B3139')
            
            st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
st.markdown("🟢 **Status**: Conectado à API oficial da Binance via ccxt. Dados sendo extraídos em tempo real.")
