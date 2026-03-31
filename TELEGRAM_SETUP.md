# 📱 Telegram Notifier - Guia de Configuração

## 🎯 **O que foi implementado:**

Sistema completo de notificações via Telegram para a Estratégia 1H, substituindo a dependência da API Binance.

## 📋 **Funcionalidades:**

### ✅ **Tipos de Notificações:**
- 🚀 **Sinais de Compra:** Quando detectada oportunidade de entrada
- 📉 **Sinais de Venda:** Quando detectada necessidade de saída  
- 📊 **Atualizações da Estratégia:** Resumo completo da análise
- 🚨 **Alertas Urgentes:** Sinais críticos que requerem atenção imediata
- 🧪 **Mensagens de Teste:** Verificação do funcionamento

### ✅ **Informações Incluídas:**
- Símbolo e preço atual
- Score de entrada (0-100)
- RSI e status das EMAs
- Motivo do sinal
- Timeframe (1H + 15m)
- Horário da análise

## 🔧 **Como Configurar:**

### 1️⃣ **Criar Bot no Telegram:**
1. Abra o Telegram e procure por **@BotFather**
2. Envie `/newbot`
3. Siga as instruções:
   - Nome do bot: `Estratégia 1H Bot`
   - Username: `estrategia1h_bot` (ou outro disponível)
4. Copie o **TOKEN** fornecido

### 2️⃣ **Obter Chat ID:**
1. Inicie uma conversa com seu bot
2. Envie qualquer mensagem (ex: "oi")
3. Abra no navegador: `https://api.telegram.org/botSEU_TOKEN/getUpdates`
4. Procure por `"chat":{"id":123456789}`
5. Copie o **CHAT ID**

### 3️⃣ **Configurar no Dashboard:**
1. Abra o dashboard: `http://localhost:8501`
2. No sidebar, preencha:
   - **🔑 Token Telegram Bot:** Seu token
   - **💬 Chat ID:** Seu chat ID
3. Clique em **"🧪 Testar Telegram"**
4. Deve receber mensagem de teste

## 🧪 **Como Testar:**

### **Teste via Dashboard:**
- Configure token e chat ID no sidebar
- Clique "🧪 Testar Telegram"
- Verifique se recebe mensagem

### **Testevia Script:**
```bash
cd "c:/Projeto anticons"
python teste_telegram_notifier.py
```

## 📊 **Exemplos de Mensagens:**

### 🚀 **Sinal de Compra:**
```
🚀 **SINAL DE COMPRA DETECTADO**

📊 **Ativo:** BTC/USDT
💰 **Preço:** $50000.000000
📈 **Score:** 85/100
📉 **RSI:** 22.50
🔄 **EMA Status:** EMA 9 < EMA 21
⏰ **Timeframe:** 1H

🔥 **Recomendação:** Considerar entrada long
📱 **Análise:** Estratégia 1H + 15m

⏰ Horário: 15:30:45
```

### 📉 **Sinal de Venda:**
```
📉 **SINAL DE VENDA DETECTADO**

📊 **Ativo:** ETH/USDT
💰 **Preço:** $3000.000000
📈 **Score:** 75/100
📉 **RSI:** 68.50
🚪 **Motivo Saída:** RSI > 70 + EMA 9 < EMA 21
⏰ **Timeframe:** 1H

🔥 **Recomendação:** Considerar saída/short
📱 **Análise:** Estratégia 1H + 15m

⏰ Horário: 15:30:45
```

### 📊 **Atualização da Estratégia:**
```
📊 **ATUALIZAÇÃO ESTRATÉGIA 1H**

🔍 **Analisados:** 10 ativos
📈 **Sinais Compra:** 2
📉 **Sinais Venda:** 0

🏆 **TOP OPORTUNIDADES:**

1. 🚀 BTC/USDT
   💰 $50000.000000
   📈 Score: 85
   📉 RSI: 22.50
   🔄 🟢 COMPRA 1H+15m CONFIRMADA

2. 🚀 ETH/USDT
   💰 $3000.000000
   📈 Score: 72
   📉 RSI: 28.00
   🔄 🟢 COMPRA 1H+15m CONFIRMADA

⏰ Horário: 15:30:45
📱 Dashboard: Estratégia 1H Crypto Scanner Pro
```

## 🚨 **Alertas Urgentes:**
```
🚨 **ALERTA URGENTE - URGENT**

📊 **Ativo:** BTC/USDT
💰 **Preço:** $52000.000000
📈 **RSI:** 78.50
📉 **Motivo:** RSI > 75 + Volume elevado

🔥 **Ação Imediata Recomendada!**
📱 **Estratégia:** 1H + 15m

⏰ Horário: 15:30:45
```

## 🔄 **Como Funciona:**

1. **Análise Automática:** Dashboard analisa criptomoedas
2. **Detecção de Sinais:** Identifica oportunidades (Score ≥ 70)
3. **Envio Automático:** Envia notificações via Telegram
4. **Múltiplos Tipos:** Compra, venda, urgentes, atualizações
5. **Sem Dependência Binance:** Funciona independentemente

## 🛠️ **Arquivos Modificados:**

### ✅ **Novos Arquivos:**
- `telegram_notifier.py` - Sistema de notificações
- `teste_telegram_notifier.py` - Script de teste

### ✅ **Arquivos Alterados:**
- `dashboard_estrategia_4h.py` - Integração com Telegram
  - Removida dependência da Binance
  - Adicionada configuração Telegram no sidebar
  - Integrado envio de notificações automáticas

## 🔒 **Segurança:**

- ✅ **Sem API Keys Binance** - Removidas completamente
- ✅ **Apenas Token Telegram** - Necessário para notificações
- ✅ **Chat ID Privado** - Apenas você recebe mensagens
- ✅ **Bot Privado** - Configure como privado se desejar

## 🎉 **Benefícios:**

- 🚀 **Notificações Imediatas** - Sinais em tempo real
- 📱 **Acesso Remoto** - Receba alertas em qualquer lugar
- 🔥 **Múltiplos Tipos** - Compra, venda, urgentes
- 📊 **Informações Completas** - Dados detalhados em cada alerta
- 🛡️ **Seguro** - Sem dependência de exchanges
- ⚡ **Rápido** - Entrega instantânea de mensagens

## 🆘 **Troubleshooting:**

### ❌ **"Bot não responde"**
- Verifique se o token está correto
- Confirme que iniciou conversa com o bot
- Teste: `https://api.telegram.org/botTOKEN/getMe`

### ❌ **"Erro 404"**
- Token inválido ou bot não existe
- Verifique com @BotFather: `/mybots`
- Copie o token novamente

### ❌ **"Sem mensagens"**
- Verifique se Score ≥ 70 para sinais
- Confirme configuração no dashboard
- Teste com o script de teste

### ❌ **"Chat ID errado"**
- Envie mensagem para o bot primeiro
- Use getUpdates para obter ID correto
- Verifique se não há espaços extras

---

## 🎯 **Próximo Passos:**

1. ✅ Configure seu bot Telegram
2. ✅ Teste as notificações
3. ✅ Execute análise no dashboard
4. ✅ Receba alertas automáticos

**Seu sistema de notificações está pronto!** 🚀
