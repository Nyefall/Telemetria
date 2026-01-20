# Changelog - Sistema de Telemetria

## v1.2.0 - Janeiro 2026 - Configurações Gerais

### 🎯 Mudanças Principais

**Configurações Gerais (Receiver)**
- ✨ **NOVO**: Painel de configurações com abas (tecla `S`)
- 🎨 **Aba Aparência**: 4 temas (Dark, Light, High Contrast, Cyberpunk) + cores customizadas por setor
- 🔔 **Aba Alertas**: Thresholds personalizáveis para temperatura/uso de CPU, GPU, RAM, Storage, Ping
- 📱 **Aba Notificações**: Integração com Telegram, Discord e ntfy.sh (push gratuito)
- 📊 **Aba Histórico**: Configuração de log CSV e retenção

**Alertas e Notificações**
- ✨ Thresholds de aviso e crítico configuráveis por métrica
- ✨ Cooldown configurável para sons e webhooks
- ✨ Suporte a ntfy.sh para notificações push gratuitas no celular

**Aparência**
- ✨ Novos temas: High Contrast (acessibilidade) e Cyberpunk
- ✨ Cores personalizáveis por setor (CPU, GPU, RAM, etc.) via código hex
- 🎨 Temas salvos persistentemente em `receiver_config.json`

**Arquivos**
- ✨ **NOVO**: `receiver_config.example.json` - exemplo de configuração
- 📝 Estrutura expandida do `receiver_config.json` com todas as opções

### ⌨️ Novos Atalhos

| Tecla | Função |
|-------|--------|
| `S` | ⚙️ Configurações Gerais (novo!) |
| `I` | Agora abre Configurações Gerais (mantido para compatibilidade) |

---

## v1.1.0 - Janeiro 2026 - Executável Unificado

### 🎯 Mudanças Principais

**Executável Unificado**
- ✨ **NOVO**: `Telemetria.exe` - um único executável com seleção de modo
- 📱 Interface gráfica de launcher para escolher entre Sender ou Receiver
- 🎨 Design moderno com botões coloridos e descrições claras
- 💾 Tamanho otimizado: 29 MB (vs 35+16 MB antes)

**Arquitetura**
- ✨ **NOVO**: `telemetria.py` - launcher principal
- 🔧 Refatoração: `sender_pc.py` e `receiver_notebook.py` agora exportam `main()`
- 📦 Scripts de build unificados em `scripts/build_unified.py`

**Documentação**
- 📝 README.md atualizado com nova estrutura
- 🗑️ Removido README.old.md (backup obsoleto)
- 📋 README.txt na pasta dist atualizado para executável único
- ✨ Novo arquivo CHANGELOG.md para tracking de versões

**Scripts**
- ✨ **NOVO**: `scripts/build_unified.py` - build do executável unificado
- ✨ **NOVO**: `scripts/RUN_TELEMETRIA.bat` - launcher via batch
- 📁 Scripts de build legado mantidos para compatibilidade

**.gitignore**
- 🧹 Adicionado *.old e *.old.* para ignorar backups
- 🧹 Adicionado *.tmp para arquivos temporários Windows
- 🧹 Melhoria geral na organização

### 📊 Comparação de Versões

| Aspecto | v1.0.0 (Legado) | v1.1.0 (Unificado) |
|---------|-----------------|---------------------|
| Executáveis | 2 arquivos separados | 1 arquivo único |
| Tamanho Total | 51 MB | 29 MB |
| Seleção de Modo | Manual (2 .exe) | Interface gráfica |
| Distribuição | Copiar 2 arquivos | Copiar 1 arquivo |
| Experiência | Técnica | User-friendly |

### 🔄 Migração de v1.0.0 para v1.1.0

**Usuários finais:**
- Substituir `TelemetriaSender.exe` e `TelemetriaReceiver.exe` por `Telemetria.exe`
- Manter `config.json` e `libs/` no mesmo local
- Executar e escolher o modo desejado

**Desenvolvedores:**
- Código fonte permanece compatível
- Novos imports: `import sender_pc` e `import receiver_notebook`
- Build: `python scripts/build_unified.py`

### 🐛 Correções

- Nenhum bug reportado na v1.0

### 📦 Arquivos do Release

```
dist/
├── Telemetria.exe          ⭐ NOVO - Executável unificado (29 MB)
├── config.json             Configuração do sender
├── libs/                   DLLs do LibreHardwareMonitor
├── README.txt              Guia de uso atualizado
├── TelemetriaSender.exe    [LEGADO] Mantido para compatibilidade
└── TelemetriaReceiver.exe  [LEGADO] Mantido para compatibilidade
```

---

## v1.0.0 - Janeiro 2026 - Release Inicial

### Funcionalidades

- ✅ Monitoramento completo de hardware (CPU, GPU, RAM, Storage, Rede)
- ✅ LibreHardwareMonitor via pythonnet
- ✅ Comunicação UDP (broadcast + manual IP)
- ✅ Magic byte protocol (0x01 gzip, 0x00 raw)
- ✅ Compressão gzip (~50% redução)
- ✅ System Tray no sender (pystray)
- ✅ Dashboard com temas claro/escuro
- ✅ Log CSV de histórico
- ✅ Notificações Windows (win10toast)
- ✅ Configuração de interface de rede (bind_ip)
- ✅ Auto-elevação para Admin (sender)

### Arquivos

- `sender_pc.py` - Sender standalone
- `receiver_notebook.py` - Receiver standalone
- `hardware_monitor.py` - Interface de sensores
- `config.json` - Configuração
- `receiver_config.json` - Config dinâmica do receiver (tecla I)

### Build

- `scripts/build_sender.py` - Build do sender
- `scripts/build_receiver.py` - Build do receiver
- `scripts/build_all.py` - Build de ambos

### Testes

- `tests/test_admin_sensors.py` - Verificação de sensores
- `tests/test_connectivity.py` - Teste de rede UDP
- `tests/test_receiver_quick.py` - Teste de recepção

---

## Roadmap Futuro

### v1.3.0 (Próxima)
- [ ] Adicionar ícone personalizado ao executável
- [ ] Interface Web (Flask/FastAPI) para acesso via navegador
- [ ] Histórico de conexões no receiver
- [ ] Suporte a múltiplos senders

### v2.0.0 (Futuro)
- [ ] Gráficos históricos (últimos 5 min, 1h, etc)
- [ ] Export de relatórios em PDF
- [ ] Modo de economia de energia
- [ ] SQLite para histórico persistente

### Ideias em Análise
- [ ] Suporte para Linux (se LibreHardwareMonitor disponibilizar)
- [ ] API REST para integração com outros sistemas
- [ ] Plugin system para sensores customizados
- [ ] Tema personalizável via CSS
