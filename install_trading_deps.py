"""
📦 Instalação das Dependências do Trading Bot
"""

import subprocess
import sys
import os

def install_package(package):
    """Instala um pacote usando pip"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"✅ {package} instalado com sucesso!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao instalar {package}: {e}")
        return False

def main():
    """Instala todas as dependências necessárias"""
    print("🚀 Instalando dependências do Trading Bot...")
    print("=" * 50)
    
    # Lista de dependências
    dependencies = [
        "python-telegram-bot",
        "python-binance", 
        "flask",
        "requests",
        "streamlit-autorefresh"  # Já deve estar instalado, mas garante
    ]
    
    # Instala cada dependência
    success_count = 0
    for dep in dependencies:
        if install_package(dep):
            success_count += 1
        print("-" * 30)
    
    # Resumo
    print(f"\n📊 Resumo da Instalação:")
    print(f"✅ Sucesso: {success_count}/{len(dependencies)} pacotes")
    print(f"❌ Falhas: {len(dependencies) - success_count}/{len(dependencies)} pacotes")
    
    if success_count == len(dependencies):
        print("\n🎉 Todas as dependências foram instaladas com sucesso!")
        print("\n📋 Próximos passos:")
        print("1. Configure seu bot no Telegram com @BotFather")
        print("2. Configure suas APIs da Binance")
        print("3. Preencha as configurações no dashboard")
        print("4. Teste a conexão com o botão '🧪 Testar Conexão'")
    else:
        print(f"\n⚠️ {len(dependencies) - success_count} pacotes falharam na instalação")
        print("Verifique os erros acima e tente manualmente:")
        for dep in dependencies:
            print(f"   pip install {dep}")

if __name__ == "__main__":
    main()
