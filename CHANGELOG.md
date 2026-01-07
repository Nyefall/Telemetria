# Changelog - Sistema de Telemetria

## v2.0 - Janeiro 2026 - Executável Unificado

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

| Aspecto | v1.0 (Legado) | v2.0 (Unificado) |
|---------|---------------|------------------|
| Executáveis | 2 arquivos separados | 1 arquivo único |
| Tamanho Total | 51 MB | 29 MB |
| Seleção de Modo | Manual (2 .exe) | Interface gráfica |
| Distribuição | Copiar 2 arquivos | Copiar 1 arquivo |
| Experiência | Técnica | User-friendly |

### 🔄 Migração de v1.0 para v2.0

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

## v1.0 - Janeiro 2026 - Release Inicial

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

### v2.1 (Próxima)
- [ ] Adicionar ícone personalizado ao executável
- [ ] Configuração de porta UDP via interface
- [ ] Histórico de conexões no receiver
- [ ] Alertas configuráveis (temperatura, uso CPU)

### v3.0 (Futuro)
- [ ] Suporte para múltiplos senders em um receiver
- [ ] Gráficos históricos (últimos 5 min, 1h, etc)
- [ ] Export de relatórios em PDF
- [ ] Modo de economia de energia

### Ideias em Análise
- [ ] Suporte para Linux (se LibreHardwareMonitor disponibilizar)
- [ ] API REST para integração com outros sistemas
- [ ] Plugin system para sensores customizados
- [ ] Tema personalizável via CSS
