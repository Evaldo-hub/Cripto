"""
🔄 Teste de Auto-Refresh do Dashboard
Verifica se o sistema de atualização automática está funcionando corretamente
"""

import streamlit as st
from datetime import datetime, timedelta, timezone

def test_auto_refresh():
    """Testa o sistema de auto-refresh"""
    
    st.title("🔄 Teste de Auto-Refresh")
    
    # Simula session state
    if 'test_last_analysis_time' not in st.session_state:
        st.session_state.test_last_analysis_time = datetime.now(timezone.utc) - timedelta(minutes=15)
    
    if 'test_auto_refresh_active' not in st.session_state:
        st.session_state.test_auto_refresh_active = False
    
    # Controle
    auto_refresh_active = st.checkbox("🔄 Atualização Automática", value=st.session_state.test_auto_refresh_active)
    st.session_state.test_auto_refresh_active = auto_refresh_active
    
    if auto_refresh_active:
        refresh_interval = st.selectbox("⏱️ Intervalo", ["1 min", "2 min", "5 min"], index=0)
        
        # Status
        st.markdown("---")
        st.markdown("### 📊 Status")
        
        last_update = st.session_state.test_last_analysis_time
        now = datetime.now(timezone.utc)
        
        interval_minutes = {
            "1 min": 1,
            "2 min": 2,
            "5 min": 5
        }.get(refresh_interval, 1)
        
        next_update = last_update + timedelta(minutes=interval_minutes)
        
        # Informações
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("🕐 Última Análise", last_update.strftime('%H:%M:%S'))
            st.metric("⏰ Próxima Análise", next_update.strftime('%H:%M:%S'))
        
        with col2:
            time_diff = now - last_update
            time_until = next_update - now
            
            st.metric("⏱️ Tempo Decorrido", f"{int(time_diff.total_seconds()/60)}min")
            st.metric("⏳ Tempo Restante", f"{int(time_until.total_seconds()/60)}min")
        
        # Verificação
        if now >= next_update:
            st.error("🔄 HORA DE ATUALIZAR!")
            if st.button("🔄 Simular Atualização"):
                st.session_state.test_last_analysis_time = now
                st.success("✅ Análise atualizada!")
                st.rerun()
        else:
            st.success("✅ Aguardando próxima atualização")
        
        # Auto-refresh com streamlit-autorefresh
        try:
            from streamlit_autorefresh import st_autorefresh
            count = st_autorefresh(interval=10000, limit=None, key="test_refresh")
            
            if count > 0 and now >= next_update:
                st.session_state.test_last_analysis_time = now
                st.success("🔄 Auto-refresh funcionou!")
                st.rerun()
                
        except ImportError:
            st.warning("⚠️ streamlit-autorefresh não instalado")
            st.code("pip install streamlit-autorefresh")
    
    else:
        st.info("📝 Ative a atualização automática para testar")
    
    # Debug
    st.markdown("---")
    st.markdown("### 🔍 Debug Info")
    st.json({
        "last_analysis_time": st.session_state.test_last_analysis_time.isoformat(),
        "auto_refresh_active": st.session_state.test_auto_refresh_active,
        "current_time": datetime.now(timezone.utc).isoformat()
    })

if __name__ == "__main__":
    test_auto_refresh()
