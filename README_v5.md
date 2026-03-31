# 🤖 Crypto Quant Scanner v5.0

Sistema de análise quantitativa de criptomoedas com arquitetura modular e cache inteligente.

## 🏗️ Arquitetura

```
           APIs de Mercado
        (Binance, Bybit, OKX)
                 │
                 ▼
         Coletor de Dados
        (via CCXT / WebSocket)
                 │
                 ▼
        Cache / Banco rápido
       (Redis ou memória)
                 │
                 ▼
           Motor Quant
    (indicadores, ranking)
                 │
                 ▼
           Dashboard
        (Streamlit / Web)
```

## 📁 Estrutura do Projeto

```
├── src/
│   ├── __init__.py
│   ├── data_collector.py    # Coleta de dados das exchanges
│   ├── cache_manager.py     # Sistema de cache inteligente
│   └── quant_engine.py      # Motor de análise quantitativa
├── dashboard_quant.py       # Interface Streamlit otimizada
├── orchestrator.py          # Orquestrador principal
├── dashboard.py             # Dashboard original (legado)
├── requirements.txt         # Dependências
├── render.yaml             # Configuração Render
└── README_v5.md             # Este arquivo
```

## 🚀 Funcionalidades

### ✅ Coletor de Dados (`src/data_collector.py`)
- Suporte a múltiplas exchanges (Binance, Bybit, OKX)
- Coleta em lote eficiente com rate limiting
- Tratamento de erros robusto
- Métodos para obter símbolos de maior volume

### ✅ Cache Inteligente (`src/cache_manager.py`)
- Cache em memória e disco
- TTL por timeframe (1m, 5m, 15m, 1h, 4h, 1d)
- Validação automática de cache expirado
- Sistema de limpeza e manutenção

### ✅ Motor Quantitativo (`src/quant_engine.py`)
- 15+ indicadores técnicos (RSI, MACD, Bollinger, etc.)
- Sistema de scoring ponderado e personalizável
- Análise em lote para múltiplos ativos
- Geração de sinais (COMPRA/VENDA/NEUTRO)

### ✅ Dashboard Otimizado (`dashboard_quant.py`)
- Interface moderna com Streamlit
- Uso exclusivo de cache (sem chamadas diretas à API)
- Visualizações avançadas com Plotly
- Métricas em tempo real

### ✅ Orquestrador (`orchestrator.py`)
- Coordena todos os componentes
- Análises agendadas automáticas
- Geração de relatórios JSON
- Modo de aquecimento de cache

## 🛠️ Instalação e Uso

### 1. Instalar dependências
```bash
pip install -r requirements.txt
```

### 2. Executar Dashboard
```bash
streamlit run dashboard_quant.py
```

### 3. Executar Análise via CLI
```bash
# Análise única
python orchestrator.py --mode single --symbols BTC/USDT ETH/USDT --timeframes 1h 4h

# Aquecer cache
python orchestrator.py --mode warmup

# Análise agendada
python orchestrator.py --mode scheduled
```

## 📊 Como Usar o Dashboard

1. **Configure os símbolos** na sidebar
2. **Escolha o timeframe** (1h, 4h, 1d, etc.)
3. **Clique em "Iniciar Análise"**
4. **Aguarde os resultados** - cache inteligente acelera o processo

## 🎯 Indicadores Utilizados

### Trend Indicators
- EMA (20, 50, 200)
- SMA (20, 50)
- MACD + Signal
- ADX
- Ichimoku Cloud

### Momentum Indicators
- RSI (14)
- Stochastic
- Williams %R
- Rate of Change

### Volatility Indicators
- Bollinger Bands
- ATR (Average True Range)

### Volume Indicators
- Volume SMA
- Volume Ratio
- VWAP

## 📈 Sistema de Scoring

O motor quantitativo utiliza pesos configuráveis:

```python
indicator_weights = {
    'rsi': 0.20,        # Força relativa
    'macd': 0.15,       # Tendência de momentum
    'volume': 0.15,     # Confirmação por volume
    'trend': 0.20,      # Direção da tendência
    'volatility': 0.10, # Oportunidade vs risco
    'momentum': 0.20    # Velocidade do movimento
}
```

## 🔄 Cache Strategy

O sistema implementa cache multi-nível:

1. **Memória**: Acesso mais rápido
2. **Disco**: Persistência entre sessões
3. **TTL**: Expiração por timeframe
4. **Validação**: Verificação automática de dados frescos

## 🚀 Deploy no Render

O projeto está configurado para deploy no Render:

- `render.yaml`: Configuração de serviço
- `runtime.txt`: Python 3.11.9
- `requirements.txt`: Dependências otimizadas

## 📝 Melhorias vs Versão Anterior

### ✅ Performance
- Cache inteligente reduz chamadas à API em 90%
- Análise em lote processa múltiplos ativos simultaneamente
- Interface não bloqueia durante análise

### ✅ Confiabilidade
- Tratamento robusto de erros
- Sistema de cache com validação
- Componentes modulares e testáveis

### ✅ Escalabilidade
- Suporte a múltiplas exchanges
- Arquitetura orientada a serviços
- Fácil adição de novos indicadores

### ✅ Usabilidade
- Interface mais responsiva
- Métricas em tempo real
- Relatórios detalhados

## 🔧 Configuração Avançada

### Personalizar Pesos dos Indicadores
```python
# Em src/quant_engine.py
engine = get_quant_engine()
engine.indicator_weights['rsi'] = 0.30  # Aumentar peso do RSI
```

### Adicionar Nova Exchange
```python
# Em src/data_collector.py
self.exchanges['kucoin'] = ccxt.kucoin({'enableRateLimit': True})
```

### Configurar TTL do Cache
```python
# Em src/cache_manager.py
self.cache_ttl['custom'] = timedelta(minutes=30)
```

## 📊 Monitoramento

O sistema gera relatórios automáticos com:

- Total de oportunidades identificadas
- Distribuição de sinais (compra/venda)
- Score médio por timeframe
- Informações do cache

## 🤝 Contribuição

1. Fork o projeto
2. Crie branch para sua feature
3. Faça commit das mudanças
4. Abra Pull Request

## 📜 Licença

MIT License - Ver arquivo LICENSE para detalhes

---

**Desenvolvido com 🤖 para análise quantitativa avançada**
