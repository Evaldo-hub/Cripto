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
tickers_input = st.sidebar.text_input("Ativos Binance (separados por vírgula)", "BTC/USDT, DEXE/USDT,ETH/USDT, SOL/USDT, AVAX/USDT, INJ/USDT")
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
        # A Binance retona UTC. Convertendo para GMT-3 (Horário de Brasília)
        df['Timestamp'] = df['Timestamp'].dt.tz_localize('UTC').dt.tz_convert('America/Sao_Paulo')
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

def verificar_anomalia_volume(ticker, exchange):
    # Puxa apenas as últimas velas de 5 minutos para identificar despejos/compras agressivas em tempo real
    try:
        bars = exchange.fetch_ohlcv(ticker, timeframe="5m", limit=12) # Última 1 hora fracionada em 5m
        if not bars:
            return None
        df_5m = pd.DataFrame(bars, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
        # A média de volume das velas recentes (excluindo a última que está rolando)
        media_vol = df_5m['Volume'].iloc[:-1].mean()
        vela_atual = df_5m.iloc[-1]
        
        # Se o volume da vela de 5m atual for MAIOR que 4x a média recente, tem treta (institucional/baleia)
        if media_vol > 0 and vela_atual['Volume'] > (media_vol * 4):
            variacao = ((vela_atual['Close'] - vela_atual['Open']) / vela_atual['Open']) * 100
            tipo = "DUMP 🩸" if variacao < 0 else "PUMP 🚀"
            return {
                "tipo": tipo,
                "variacao": f"{variacao:.2f}%",
                "multiplicador_vol": round(vela_atual['Volume'] / media_vol, 1)
            }
        return None
    except:
        return None

tickers = [t.strip() for t in tickers_input.split(',')]

col1, col2, col3 = st.columns(3)

if 'analise_iniciada' not in st.session_state:
    st.session_state.analise_iniciada = False

if st.sidebar.button("🚀 Iniciar Análise Global"):
    st.session_state.analise_iniciada = True

if st.session_state.analise_iniciada:
    with st.spinner("Conectando aos provedores de liquidez e analisando dados..."):
        resultados = []
        
        for ticker in tickers:
            exchange = ccxt.binance({'enableRateLimit': True})
            df = load_data(ticker, interval=timeframe)
            if df is not None and len(df) > 60:
                df = apply_indicators(df)
                last_row = df.iloc[-1]
                current_price = last_row['Close']
                
                score, sinal, motivo = calcular_score_sinal(last_row, current_price)
                
                anomalia = verificar_anomalia_volume(ticker, exchange)
                
                resultados.append({
                    "Ativo": ticker.replace("/USDT", ""),
                    "Preço": current_price,
                    "Score": score,
                    "Sinal": sinal,
                    "RSI": last_row['RSI'],
                    "Volume 24h": last_row['Volume'],
                    "Status": "Normal" if score < 70 else "Breakout Provável",
                    "Observação": motivo,
                    "Anomalia_5m": anomalia
                })
        
        if resultados:
            df_res = pd.DataFrame(resultados).sort_values(by="Score", ascending=False)
            
            # --- Alertas de Radar de Alta Frequência (Baleias/Dumps) ---
            alertas_baleia = [r for r in resultados if r["Anomalia_5m"] is not None]
            if alertas_baleia:
                st.markdown("<h3 style='color: #F6465D;'>🚨 RADAR DE ALTA FREQUÊNCIA: MOVIMENTO INSTITUCIONAL DETECTADO AGORA!</h3>", unsafe_allow_html=True)
                cols_alert = st.columns(len(alertas_baleia))
                for idx, alerta in enumerate(alertas_baleia):
                    dados_anomalia = alerta["Anomalia_5m"]
                    cor = "#F6465D" if "DUMP" in dados_anomalia['tipo'] else "#0ECB81"
                    cols_alert[idx].markdown(f"""
                    <div style="background-color: rgba(246, 70, 93, 0.1); border-left: 5px solid {cor}; padding: 15px; margin-bottom: 20px;">
                        <h4 style="margin:0; color:{cor};">{alerta['Ativo']} - {dados_anomalia['tipo']}</h4>
                        <p style="margin:5px 0 0 0;">Volume <b>{dados_anomalia['multiplicador_vol']}x maior</b> que a média nos últimos 5 minutos!</p>
                        <p style="margin:0;">Variação rápida: <b>{dados_anomalia['variacao']}</b></p>
                    </div>
                    """, unsafe_allow_html=True)
            
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
            
            # Removemos a coluna interna de anomalia do display do usuário, já que ela é um dict complexo
            df_display = df_res.drop(columns=['Anomalia_5m']) if 'Anomalia_5m' in df_res.columns else df_res
            st.dataframe(df_display.style.map(map_color, subset=['Sinal']), use_container_width=True)
            
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
            
            # --- NOVO: Histórico de Sinais ---
            st.markdown("---")
            st.subheader("🕒 Histórico Analítico por Ativo")
            
            # Dropdown para selecionar a cripto desejada
            ativos_disponiveis = df_res['Ativo'].tolist()
            ativo_selecionado = st.selectbox("Selecione a Cripto para ver o Histórico:", ativos_disponiveis)
            
            # Carregar dados da cripto selecionada (se não for a top_coin que já está na RAM)
            if ativo_selecionado == top_coin['Ativo']:
                df_history_plot = df_plot # Já carregado para o gŕafico acima
            else:
                with st.spinner(f"Carregando histórico de {ativo_selecionado}..."):
                    df_history_raw = load_data(ativo_selecionado+"/USDT", interval=timeframe)
                    df_history_plot = apply_indicators(df_history_raw)
            
            history_data = []
            
            # Pegar as últimas 20 velas para o relatório de tempo/hora
            for timestamp, row in df_history_plot.tail(20).iterrows():
                h_score, h_sinal, h_motivo = calcular_score_sinal(row, row['Close'])
                history_data.append({
                    "Data/Hora": timestamp.strftime("%Y-%m-%d %H:%M"),
                    "Preço (USDT)": f"${row['Close']:.2f}",
                    "Sinal": h_sinal,
                    "Score": h_score,
                    "Critérios Alcançados": h_motivo
                })
                
            history_df = pd.DataFrame(history_data)
            # Inverter para mostrar a vela mais recente no topo
            history_df = history_df.iloc[::-1].reset_index(drop=True)
            
            st.dataframe(history_df.style.map(map_color, subset=['Sinal']), use_container_width=True)

st.markdown("---")
st.markdown("🟢 **Status**: Conectado à API oficial da Binance via ccxt. Dados sendo extraídos em tempo real.")
