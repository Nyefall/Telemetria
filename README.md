# Central de Telemetria (PC -> Notebook)

Este projeto permite monitorar o desempenho do seu PC Principal (Sender) utilizando a tela do seu Notebook (Receiver) como um painel de telemetria dedicado, via rede local.

## Funcionalidades

*   **Monitoramento em Tempo Real:**
    *   Uso de CPU, GPU e RAM.
    *   Temperaturas (CPU e GPU).
    *   Velocidade de Rede (Upload/Download).
    *   Latência e Ping entre as máquinas.
*   **Visualização Gráfica:** Dashboard completo rodando no notebook com gráficos históricos (últimos 60s).
*   **Baixo Impacto:** O Sender é otimizado para não impactar o desempenho dos jogos.

## Pré-requisitos

1.  **Python 3.8+** instalado em ambas as máquinas.
2.  **Conexão de Rede:** Idealmente via cabo Ethernet direto ou Switch Gigabit para menor latência, mas funciona via Wi-Fi.
3.  **LibreHardwareMonitor (Opcional):** Recomendado no PC Principal para obter leituras precisas de Voltagem e Temperatura da CPU via WMI.

## Instalação

1.  Clone este repositório em ambas as máquinas.
2.  Instale as dependências:

```bash
pip install -r requirements.txt
```

> **Nota:** No Notebook (Receiver), a biblioteca `pyadl`, `wmi` e `psutil` podem não ser estritamente necessárias se ele for apenas exibir, mas o `matplotlib` é essencial. Recomendo instalar tudo para garantir compatibilidade.

## Configuração

1.  Descubra o IP do Notebook:
    *   Abra o terminal no notebook e digite `ipconfig` (Windows) ou `ip a` (Linux).
    *   Anote o endereço (ex: `192.168.10.137`).
2.  Edite o arquivo `sender_pc.py` no PC Principal:
    *   Atualize a variável `NOTEBOOK_IP` com o IP anotado.

## Como Usar

### 1. No PC Principal (Sender)
Execute o script que coleta e envia os dados:

```bash
python sender_pc.py
```

### 2. No Notebook (Receiver)
Execute o script que abre o dashboard:

```bash
python receiver_notebook.py
```

## Solução de Problemas

*   **Gráficos não aparecem / "Aguardando dados...":** Verifique se o Firewall do Windows no notebook permitiu a conexão Python na porta UDP 5005. Tente desativar firewall temporariamente para testar.
*   **Temperatura GPU "N/A":** Se sua placa não for AMD, reinstale drivers ou verifique compatibilidade. Para Nvidia, futuras atualizações podem ser necessárias (requer bibliotecas proprietárias `nvml`).
*   **Voltagem CPU Zerada:** Certifique-se de que o *LibreHardwareMonitor* está aberto e rodando no PC Principal.
