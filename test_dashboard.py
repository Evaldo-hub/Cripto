import streamlit as st
import sys
import os

# Adiciona src ao path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

st.set_page_config(page_title="Test Dashboard", layout="wide")

st.title("🧪 Test Dashboard Simplificado")

st.sidebar.title("Controles")

if st.sidebar.button("🔍 Testar Import"):
    try:
        from parallel_collector import get_parallel_collector
        from trading_bot import create_trading_bot
        st.success("✅ Imports funcionando!")
        
        collector = get_parallel_collector(max_workers=5)
        symbols = collector.get_usdt_symbols('binance', min_volume=0)
        st.info(f"📊 {len(symbols)} símbolos encontrados")
        
    except Exception as e:
        st.error(f"❌ Erro: {e}")
        import traceback
        st.error(traceback.format_exc())

if st.sidebar.button("🚀 Testar Análise"):
    try:
        from parallel_collector import get_parallel_collector
        from dashboard_estrategia_4h import Estrategia1hEngine
        
        st.info("🔄 Iniciando teste...")
        
        collector = get_parallel_collector(max_workers=5)
        engine = Estrategia1hEngine()
        
        # Teste com BTC
        st.info("📈 Testando com BTC/USDT...")
        df = collector.fetch_single_symbol(('BTC/USDT', '1h', 100, 'binance'))
        
        if df is not None and len(df) > 0:
            st.success(f"✅ BTC: {len(df)} candles coletados")
            
            # Teste de análise
            result = engine.analyze_symbol_estrategia('BTC/USDT', collector)
            
            if 'error' not in result:
                st.success(f"✅ Análise OK - Score: {result.get('score_entrada', 0)}")
                st.json(result)
            else:
                st.error(f"❌ Erro na análise: {result.get('error', 'Unknown')}")
        else:
            st.error("❌ Sem dados para BTC")
            
    except Exception as e:
        st.error(f"❌ Erro: {e}")
        import traceback
        st.error(traceback.format_exc())
