"""
Script para baixar as dependências do LibreHardwareMonitor.
Baixa o release oficial e extrai as DLLs necessárias.
"""
import os
import urllib.request
import zipfile
import shutil

# Pasta de destino
libs_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "libs")

# URL do release do LibreHardwareMonitor (versão estável)
# O pacote NuGet contém todas as DLLs necessárias
NUGET_URL = "https://www.nuget.org/api/v2/package/LibreHardwareMonitorLib/0.9.3"
ZIP_PATH = os.path.join(libs_folder, "lhm_package.zip")
EXTRACT_PATH = os.path.join(libs_folder, "temp_extract")

# DLLs necessárias (net472 para compatibilidade)
REQUIRED_DLLS = [
    "LibreHardwareMonitorLib.dll",
    "HidSharp.dll"
]

def download_and_extract():
    print(f"Baixando LibreHardwareMonitorLib do NuGet...")
    print(f"URL: {NUGET_URL}")
    
    try:
        urllib.request.urlretrieve(NUGET_URL, ZIP_PATH)
        print(f"Download concluído: {ZIP_PATH}")
    except Exception as e:
        print(f"Erro no download: {e}")
        return False
    
    print(f"Extraindo pacote...")
    try:
        with zipfile.ZipFile(ZIP_PATH, 'r') as zip_ref:
            zip_ref.extractall(EXTRACT_PATH)
        print(f"Extração concluída")
    except Exception as e:
        print(f"Erro na extração: {e}")
        return False
    
    # Procura as DLLs em lib/net472 ou lib/netstandard2.0
    net_folders = ["lib/net472", "lib/netstandard2.0", "lib/net462"]
    
    for net_folder in net_folders:
        source_folder = os.path.join(EXTRACT_PATH, net_folder.replace("/", os.sep))
        if os.path.exists(source_folder):
            print(f"Encontrado: {net_folder}")
            for dll in REQUIRED_DLLS:
                src = os.path.join(source_folder, dll)
                dst = os.path.join(libs_folder, dll)
                if os.path.exists(src):
                    shutil.copy2(src, dst)
                    print(f"  Copiado: {dll}")
                else:
                    print(f"  Não encontrado: {dll}")
    
    # Limpa arquivos temporários
    print("Limpando temporários...")
    os.remove(ZIP_PATH)
    shutil.rmtree(EXTRACT_PATH)
    
    print("\nVerificando DLLs na pasta libs:")
    for f in os.listdir(libs_folder):
        if f.endswith(".dll"):
            print(f"  ✓ {f}")
    
    return True

if __name__ == "__main__":
    print("=" * 50)
    print("INSTALADOR DE DEPENDÊNCIAS - LibreHardwareMonitor")
    print("=" * 50)
    
    if not os.path.exists(libs_folder):
        os.makedirs(libs_folder)
    
    if download_and_extract():
        print("\n✓ Dependências instaladas com sucesso!")
    else:
        print("\n✗ Falha na instalação das dependências")
