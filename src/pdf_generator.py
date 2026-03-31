"""
PDF Report Generator
Gera relatórios em PDF para as análises de criptomoedas
"""
from datetime import datetime
from typing import List, Dict
import os
from fpdf2 import FPDF
import pandas as pd

class CryptoPDFReport(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)
        self.set_margins(15, 15, 15)
        
    def header(self):
        """Cabeçalho do relatório"""
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'Crypto Scanner - Relatório de Análise', 0, 1, 'C')
        self.set_font('Arial', 'I', 10)
        self.cell(0, 8, f'Gerado em: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}', 0, 1, 'C')
        self.ln(10)
    
    def footer(self):
        """Rodapé do relatório"""
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')
    
    def chapter_title(self, title):
        """Título de capítulo"""
        self.set_font('Arial', 'B', 14)
        self.set_fill_color(200, 220, 255)
        self.cell(0, 10, title, 0, 1, 'L', 1)
        self.ln(5)
    
    def chapter_body(self, body):
        """Corpo do capítulo"""
        self.set_font('Arial', '', 12)
        self.multi_cell(0, 10, body)
        self.ln()
    
    def add_summary_table(self, results: List):
        """Adiciona tabela resumo de resultados"""
        self.chapter_title('Resumo da Análise')
        
        # Estatísticas
        total = len(results)
        buy_signals = len([r for r in results if "COMPRA" in r.signal])
        sell_signals = len([r for r in results if "VENDA" in r.signal])
        avg_score = sum(r.score for r in results) / total if results else 0
        
        # Tabela de estatísticas
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'Estatísticas Gerais:', 0, 1, 'L')
        self.set_font('Arial', '', 11)
        
        stats_text = f"""
• Total de Símbolos Analisados: {total}
• Sinais de Compra: {buy_signals}
• Sinais de Venda: {sell_signals}
• Score Médio: {avg_score:.2f}
• Data da Análise: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}
        """
        self.multi_cell(0, 8, stats_text)
        self.ln(10)
    
    def add_opportunities_table(self, results: List, limit: int = None):
        """Adiciona tabela de oportunidades"""
        self.chapter_title('Oportunidades Encontradas')
        
        # Usa todos os resultados se limit for None
        display_results = results if limit is None else results[:limit]
        
        # Cabeçalho da tabela
        headers = ['Símbolo', 'Sinal', 'Score', 'Preço', 'Confiança', 'Data/Hora']
        widths = [25, 20, 15, 20, 15, 25]
        
        self.set_font('Arial', 'B', 9)  # Fonte menor para mais colunas
        for i, header in enumerate(headers):
            self.cell(widths[i], 7, header, 1, 0, 'C')
        self.ln()
        
        # Dados da tabela
        self.set_font('Arial', '', 8)  # Fonte pequena para muitos dados
        
        for result in display_results:
            symbol = result.symbol.replace("/USDT", "")
            signal = result.signal
            score = f"{result.score:.1f}"
            price = f"${result.price:.4f}"
            confidence = f"{result.confidence:.1f}%"
            timestamp = result.signal_timestamp.strftime("%d/%m %H:%M") if result.signal_timestamp else "N/A"
            
            # Cor baseada no sinal
            if "COMPRA" in signal:
                self.set_fill_color(220, 255, 220)  # Verde claro
            elif "VENDA" in signal:
                self.set_fill_color(255, 220, 220)  # Vermelho claro
            else:
                self.set_fill_color(255, 255, 220)  # Amarelo claro
            
            self.cell(widths[0], 6, symbol, 1, 0, 'C', 1)
            self.cell(widths[1], 6, signal, 1, 0, 'C', 1)
            self.cell(widths[2], 6, score, 1, 0, 'C', 1)
            self.cell(widths[3], 6, price, 1, 0, 'C', 1)
            self.cell(widths[4], 6, confidence, 1, 0, 'C', 1)
            self.cell(widths[5], 6, timestamp, 1, 1, 'C', 1)
        
        self.ln(10)
    
    def add_detailed_analysis(self, results: List, limit: int = 5):
        """Adiciona análise detalhada"""
        self.chapter_title('Análise Detalhada')
        
        top_results = results[:limit]
        
        for i, result in enumerate(top_results, 1):
            # Título do símbolo
            self.set_font('Arial', 'B', 12)
            if "COMPRA" in result.signal:
                self.set_text_color(0, 128, 0)  # Verde
            elif "VENDA" in result.signal:
                self.set_text_color(255, 0, 0)  # Vermelho
            else:
                self.set_text_color(255, 128, 0)  # Laranja
            
            self.cell(0, 10, f"{i}. {result.symbol} - {result.signal} (Score: {result.score:.1f})", 0, 1, 'L')
            self.set_text_color(0, 0, 0)  # Preto
            
            # Informações básicas
            self.set_font('Arial', '', 10)
            info_text = f"""
Preço Atual: ${result.price:.4f}
Confiança: {result.confidence:.1f}%
Data/Hora do Sinal: {result.signal_timestamp.strftime("%d/%m/%Y %H:%M:%S") if result.signal_timestamp else "N/A"}
            """
            self.multi_cell(0, 6, info_text)
            
            # Indicadores
            self.set_font('Arial', 'B', 10)
            self.cell(0, 6, 'Indicadores Técnicos:', 0, 1, 'L')
            self.set_font('Arial', '', 9)
            
            indicators_text = ""
            for indicator, value in result.indicators.items():
                if value is not None:
                    indicators_text += f"• {indicator.upper()}: {value}\n"
            
            self.multi_cell(0, 5, indicators_text)
            
            # Scores detalhados
            self.set_font('Arial', 'B', 10)
            self.cell(0, 6, 'Scores Detalhados:', 0, 1, 'L')
            self.set_font('Arial', '', 9)
            
            scores_text = ""
            for score_name, score_value in result.detailed_scores.items():
                scores_text += f"• {score_name.replace('_', ' ').title()}: {score_value:.1f}\n"
            
            self.multi_cell(0, 5, scores_text)
            self.ln(8)
    
    def add_disclaimer(self):
        """Adiciona disclaimer do relatório"""
        self.set_font('Arial', 'I', 8)
        self.set_fill_color(240, 240, 240)
        disclaimer_text = """
Disclaimer: Este relatório é gerado por algoritmos de análise técnica e não constitui 
recomendação de investimento. Criptomoedas são ativos de alto risco. 
Faça sua própria pesquisa antes de tomar decisões de investimento.
        """
        self.multi_cell(0, 5, disclaimer_text)
        self.ln()

def generate_pdf_report(results: List, filename: str = None) -> str:
    """Gera relatório PDF das análises"""
    try:
        if not results:
            raise ValueError("Nenhum resultado para gerar relatório")
        
        # Nome do arquivo
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"crypto_analysis_report_{timestamp}.pdf"
        
        # Cria o PDF
        pdf = CryptoPDFReport()
        pdf.add_page()
        
        # Adiciona seções
        pdf.add_summary_table(results)
        pdf.add_opportunities_table(results, limit=None)  # Todos os resultados
        pdf.add_detailed_analysis(results, limit=5)  # Apenas top 5 para detalhes
        pdf.add_disclaimer()
        
        # Salva o arquivo
        pdf.output(filename)
        
        return filename
        
    except Exception as e:
        print(f"Erro ao gerar PDF: {e}")
        return ""

def generate_simple_pdf(results: List, filename: str = None) -> str:
    """Gera versão simplificada do PDF"""
    try:
        if not results:
            raise ValueError("Nenhum resultado para gerar relatório")
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"crypto_simple_report_{timestamp}.pdf"
        
        pdf = CryptoPDFReport()
        pdf.add_page()
        
        # Título
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, 'Relatório de Análise - Crypto Scanner', 0, 1, 'C')
        pdf.set_font('Arial', 'I', 10)
        pdf.cell(0, 8, f'Gerado em: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}', 0, 1, 'C')
        pdf.ln(15)
        
        # Estatísticas rápidas
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, 'Resumo Rápido:', 0, 1, 'L')
        
        total = len(results)
        buy_signals = len([r for r in results if "COMPRA" in r.signal])
        sell_signals = len([r for r in results if "VENDA" in r.signal])
        avg_score = sum(r.score for r in results) / total if results else 0
        
        pdf.set_font('Arial', '', 11)
        summary = f"Total: {total} | Compras: {buy_signals} | Vendas: {sell_signals} | Score Médio: {avg_score:.1f}"
        pdf.cell(0, 8, summary, 0, 1, 'C')
        pdf.ln(15)
        
        # Top resultados em tabela (todos os resultados)
        pdf.set_font('Arial', 'B', 11)
        headers = ['Símbolo', 'Sinal', 'Score', 'Preço', 'Data/Hora']
        widths = [30, 25, 15, 25, 35]
        
        for i, header in enumerate(headers):
            pdf.cell(widths[i], 8, header, 1, 0, 'C')
        pdf.ln()
        
        pdf.set_font('Arial', '', 8)  # Fonte menor para caber mais dados
        for result in results:  # Todos os resultados, não apenas top 10
            symbol = result.symbol.replace("/USDT", "")
            signal = result.signal
            score = f"{result.score:.1f}"
            price = f"${result.price:.4f}"
            timestamp = result.signal_timestamp.strftime("%d/%m %H:%M") if result.signal_timestamp else "N/A"
            
            # Cor baseada no sinal
            if "COMPRA" in signal:
                pdf.set_fill_color(220, 255, 220)
            elif "VENDA" in signal:
                pdf.set_fill_color(255, 220, 220)
            else:
                pdf.set_fill_color(255, 255, 220)
            
            pdf.cell(widths[0], 6, symbol, 1, 0, 'C', 1)
            pdf.cell(widths[1], 6, signal, 1, 0, 'C', 1)
            pdf.cell(widths[2], 6, score, 1, 0, 'C', 1)
            pdf.cell(widths[3], 6, price, 1, 0, 'C', 1)
            pdf.cell(widths[4], 6, timestamp, 1, 1, 'C', 1)
        
        pdf.output(filename)
        return filename
        
    except Exception as e:
        print(f"Erro ao gerar PDF simples: {e}")
        return ""

if __name__ == "__main__":
    # Teste do gerador de PDF
    from simple_quant_engine import SimpleAnalysisResult
    
    # Cria dados de teste
    test_results = [
        SimpleAnalysisResult(
            symbol="BTC/USDT",
            price=45000.0,
            score=75.5,
            signal="COMPRA_FORTE",
            confidence=85.0,
            indicators={'rsi': 45.2, 'macd': 123.4},
            detailed_scores={'rsi_score': 80, 'macd_score': 70, 'overall_score': 75.5},
            timestamp=datetime.now(),
            processing_time=0.1,
            signal_timestamp=datetime.now()
        ),
        SimpleAnalysisResult(
            symbol="ETH/USDT",
            price=3000.0,
            score=25.5,
            signal="VENDA",
            confidence=65.0,
            indicators={'rsi': 75.2, 'macd': -50.4},
            detailed_scores={'rsi_score': 20, 'macd_score': 30, 'overall_score': 25.5},
            timestamp=datetime.now(),
            processing_time=0.1,
            signal_timestamp=datetime.now()
        )
    ]
    
    # Gera PDF
    filename = generate_pdf_report(test_results)
    print(f"PDF gerado: {filename}")
    
    # Gera PDF simples
    simple_filename = generate_simple_pdf(test_results)
    print(f"PDF simples gerado: {simple_filename}")
