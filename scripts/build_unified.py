"""
Script de build do executável UNIFICADO da Telemetria
Gera um único .exe que permite ao usuário escolher entre Sender ou Receiver
"""
import PyInstaller.__main__
import shutil
import os

print("=" * 60)
print("BUILD DO TELEMETRIA - EXECUTÁVEL UNIFICADO")
print("=" * 60)

# Configuração do PyInstaller
PyInstaller.__main__.run([
    'telemetria.py',                      # Script principal (launcher)
    '--name=Telemetria',                  # Nome do executável
    '--onefile',                          # Executável único
    '--windowed',                         # Sem console
    '--icon=NONE',                        # Sem ícone (pode adicionar depois)
    '--clean',                            # Limpar cache
    
    # Incluir módulos Python locais como dados
    '--add-data=sender_pc.py;.',
    '--add-data=receiver_notebook.py;.',
    '--add-data=hardware_monitor.py;.',
    '--add-data=config.json;.',
    '--add-data=libs;libs',
    
    # Hidden imports para dependências
    '--hidden-import=psutil',
    '--hidden-import=pystray',
    '--hidden-import=PIL',
    '--hidden-import=PIL.Image',
    '--hidden-import=PIL.ImageDraw',
    '--hidden-import=win10toast',
    '--hidden-import=clr',
    '--hidden-import=pythonnet',
    
    # Coletar todos os submodules necessários
    '--collect-all=pystray',
    '--collect-all=win10toast',
])

print()
print("\nCopiando arquivos de configuração...")

# Copiar arquivos necessários para dist/
dist_path = os.path.join(os.getcwd(), 'dist')
if os.path.exists(dist_path):
    # Copiar config.json se não existir
    config_dest = os.path.join(dist_path, 'config.json')
    if not os.path.exists(config_dest):
        shutil.copy('config.json', config_dest)
        print(f"✓ config.json copiado")
    
    # Copiar pasta libs se não existir
    libs_dest = os.path.join(dist_path, 'libs')
    if not os.path.exists(libs_dest):
        shutil.copytree('libs', libs_dest)
        print(f"✓ libs/ copiado")

print()
print("=" * 60)
print("✓ BUILD CONCLUÍDO!")
print(f"Executável: {os.path.join(dist_path, 'Telemetria.exe')}")
print("=" * 60)
print()
print("INSTRUÇÕES DE USO:")
print("  1. Execute Telemetria.exe")
print("  2. Escolha o modo: Sender ou Receiver")
print("  3. O Sender requer privilégios de Administrador")
print("=" * 60)
