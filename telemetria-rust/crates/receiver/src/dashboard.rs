//! Dashboard principal – App eframe/egui.

use crate::net_thread::{self, NetMessage};
use crate::panels;
use crate::theme_egui::{self, EguiTheme};
use crossbeam_channel::Receiver;
use egui::{Color32, RichText};
use egui_plot::{Line, Plot, PlotPoints};
use std::collections::VecDeque;
use std::time::Instant;
use telemetry_core::config::AppConfig;
use telemetry_core::types::TelemetryPayload;
use tracing::info;

const HISTORY_SIZE: usize = 120; // 2 minutos a 1 pps
const CONNECTION_TIMEOUT_SECS: f64 = 5.0;

/// Estado do dashboard.
pub struct TelemetryDashboard {
    config: AppConfig,
    theme: EguiTheme,
    theme_index: usize,
    all_themes: Vec<EguiTheme>,

    // Dados
    rx: Receiver<NetMessage>,
    current_data: Option<TelemetryPayload>,
    last_data_time: Option<Instant>,
    source_addr: String,
    packet_size: usize,

    // Histórico para gráficos
    history: HistoryData,

    // UI state
    show_graphs: bool,
    is_fullscreen: bool,
}

struct HistoryData {
    cpu_usage: VecDeque<f64>,
    cpu_temp: VecDeque<f64>,
    gpu_load: VecDeque<f64>,
    gpu_temp: VecDeque<f64>,
    ram: VecDeque<f64>,
    net_down: VecDeque<f64>,
    net_up: VecDeque<f64>,
    ping: VecDeque<f64>,
}

impl HistoryData {
    fn new() -> Self {
        Self {
            cpu_usage: VecDeque::with_capacity(HISTORY_SIZE),
            cpu_temp: VecDeque::with_capacity(HISTORY_SIZE),
            gpu_load: VecDeque::with_capacity(HISTORY_SIZE),
            gpu_temp: VecDeque::with_capacity(HISTORY_SIZE),
            ram: VecDeque::with_capacity(HISTORY_SIZE),
            net_down: VecDeque::with_capacity(HISTORY_SIZE),
            net_up: VecDeque::with_capacity(HISTORY_SIZE),
            ping: VecDeque::with_capacity(HISTORY_SIZE),
        }
    }

    fn push(&mut self, p: &TelemetryPayload) {
        Self::push_deque(&mut self.cpu_usage, p.cpu.usage as f64);
        Self::push_deque(&mut self.cpu_temp, p.cpu.temp as f64);
        Self::push_deque(&mut self.gpu_load, p.gpu.load as f64);
        Self::push_deque(&mut self.gpu_temp, p.gpu.temp as f64);
        Self::push_deque(&mut self.ram, p.ram.percent as f64);
        Self::push_deque(&mut self.net_down, p.network.down_kbps as f64);
        Self::push_deque(&mut self.net_up, p.network.up_kbps as f64);
        Self::push_deque(&mut self.ping, p.network.ping_ms as f64);
    }

    fn push_deque(deque: &mut VecDeque<f64>, val: f64) {
        if deque.len() >= HISTORY_SIZE {
            deque.pop_front();
        }
        deque.push_back(val);
    }
}

impl TelemetryDashboard {
    pub fn new(_cc: &eframe::CreationContext<'_>, config: AppConfig) -> Self {
        let recv_cfg = &config.receiver;

        // Inicia thread de rede
        let rx = net_thread::spawn_receiver_thread(recv_cfg.port, recv_cfg.sender_ip.clone());

        // Carrega tema
        let all_themes = theme_egui::all_themes();
        let theme_index = all_themes
            .iter()
            .position(|t| t.name == recv_cfg.theme)
            .unwrap_or(0);
        let theme = all_themes[theme_index].clone();

        Self {
            config,
            theme,
            theme_index,
            all_themes,
            rx,
            current_data: None,
            last_data_time: None,
            source_addr: String::new(),
            packet_size: 0,
            history: HistoryData::new(),
            show_graphs: false,
            is_fullscreen: false,
        }
    }

    /// Processa mensagens pendentes da thread de rede.
    fn poll_network(&mut self) {
        // Drena todas as mensagens pendentes, fica com a mais recente
        while let Ok(msg) = self.rx.try_recv() {
            self.history.push(&msg.payload);
            self.current_data = Some(msg.payload);
            self.last_data_time = Some(Instant::now());
            self.source_addr = msg.source_addr;
            self.packet_size = msg.raw_size;
        }
    }

    fn is_connected(&self) -> bool {
        self.last_data_time
            .is_some_and(|t| t.elapsed().as_secs_f64() < CONNECTION_TIMEOUT_SECS)
    }

    /// Renderiza os gráficos de histórico.
    fn render_graphs(&self, ui: &mut egui::Ui) {
        let available_width = ui.available_width();
        let plot_height = 120.0;

        ui.horizontal_wrapped(|ui: &mut egui::Ui| {
            // CPU Usage + Temp
            let w = (available_width / 4.0) - 8.0;
            ui.vertical(|ui: &mut egui::Ui| {
                self.mini_plot(ui, "CPU %", &self.history.cpu_usage, self.theme.cpu, w, plot_height, 100.0);
            });
            ui.vertical(|ui: &mut egui::Ui| {
                self.mini_plot(ui, "CPU °C", &self.history.cpu_temp, self.theme.cpu, w, plot_height, 100.0);
            });
            ui.vertical(|ui: &mut egui::Ui| {
                self.mini_plot(ui, "GPU %", &self.history.gpu_load, self.theme.gpu, w, plot_height, 100.0);
            });
            ui.vertical(|ui: &mut egui::Ui| {
                self.mini_plot(ui, "RAM %", &self.history.ram, self.theme.ram, w, plot_height, 100.0);
            });
        });
    }

    fn mini_plot(
        &self,
        ui: &mut egui::Ui,
        label: &str,
        data: &VecDeque<f64>,
        color: Color32,
        width: f32,
        height: f32,
        y_max: f64,
    ) {
        ui.label(RichText::new(label).color(color).monospace().size(11.0));

        let points: PlotPoints = data
            .iter()
            .enumerate()
            .map(|(i, &v)| [i as f64, v])
            .collect();

        let line = Line::new(points).color(color).width(1.5);

        Plot::new(format!("plot_{label}"))
            .height(height)
            .width(width)
            .show_axes(false)
            .show_grid(false)
            .allow_drag(false)
            .allow_zoom(false)
            .allow_scroll(false)
            .allow_boxed_zoom(false)
            .include_y(0.0)
            .include_y(y_max)
            .show(ui, |plot_ui| {
                plot_ui.line(line);
            });
    }
}

impl eframe::App for TelemetryDashboard {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        // ── Poll rede ──
        self.poll_network();

        // ── Solicitar repaint contínuo (60 FPS) ──
        ctx.request_repaint_after(std::time::Duration::from_millis(16));

        // ── Configurar estilo visual baseado no tema ──
        let mut visuals = if self.theme.name == "light" {
            egui::Visuals::light()
        } else {
            egui::Visuals::dark()
        };
        visuals.panel_fill = self.theme.bg;
        visuals.window_fill = self.theme.panel;
        visuals.override_text_color = Some(self.theme.text);
        ctx.set_visuals(visuals);

        // ── Atalhos de teclado ──
        ctx.input(|i: &egui::InputState| {
            if i.key_pressed(egui::Key::G) {
                self.show_graphs = !self.show_graphs;
            }
            if i.key_pressed(egui::Key::T) {
                self.theme_index = (self.theme_index + 1) % self.all_themes.len();
                self.theme = self.all_themes[self.theme_index].clone();
                info!("Tema: {}", self.theme.name);
            }
            if i.key_pressed(egui::Key::Q) || i.key_pressed(egui::Key::Escape) {
                ctx.send_viewport_cmd(egui::ViewportCommand::Close);
            }
            if i.key_pressed(egui::Key::F) || i.key_pressed(egui::Key::F11) {
                self.is_fullscreen = !self.is_fullscreen;
                ctx.send_viewport_cmd(egui::ViewportCommand::Fullscreen(self.is_fullscreen));
            }
        });

        // ── Painel central ──
        egui::CentralPanel::default().show(ctx, |ui: &mut egui::Ui| {
            // ── Título ──
            ui.vertical_centered(|ui: &mut egui::Ui| {
                ui.label(
                    RichText::new("⚡ TELEMETRY CENTER ⚡")
                        .color(self.theme.title)
                        .size(22.0)
                        .strong()
                        .monospace(),
                );
            });

            // ── Status de conexão ──
            ui.vertical_centered(|ui: &mut egui::Ui| {
                if self.is_connected() {
                    let elapsed = self.last_data_time.unwrap().elapsed();
                    ui.label(
                        RichText::new(format!(
                            "● Conectado a {} | {} bytes | {:.0}ms atrás",
                            self.source_addr,
                            self.packet_size,
                            elapsed.as_millis()
                        ))
                        .color(Color32::from_rgb(0, 255, 136))
                        .monospace(),
                    );
                } else {
                    ui.label(
                        RichText::new(format!(
                            "○ Aguardando dados na porta {}...",
                            self.config.receiver.port
                        ))
                        .color(self.theme.critical)
                        .monospace(),
                    );
                }
            });

            ui.add_space(8.0);

            if let Some(ref data) = self.current_data {
                let th = &self.config.receiver.alerts;
                let expected_link = self.config.receiver.expected_link_speed_mbps;

                // ── Row 1: CPU | GPU | RAM ──
                ui.columns(3, |cols| {
                    panels::render_cpu(&mut cols[0], &data.cpu, &self.theme, th);
                    panels::render_gpu(&mut cols[1], &data.gpu, &self.theme, th);
                    panels::render_ram(&mut cols[2], &data.ram, &self.theme, th);
                });

                ui.add_space(6.0);

                // ── Row 2: MOBO | STORAGE | NETWORK ──
                ui.columns(3, |cols| {
                    panels::render_mobo(&mut cols[0], &data.mobo, &data.fans, &self.theme);
                    panels::render_storage(&mut cols[1], &data.storage, &self.theme, th);
                    panels::render_network(&mut cols[2], &data.network, &self.theme, th, expected_link);
                });

                // ── Gráficos ──
                if self.show_graphs {
                    ui.add_space(8.0);
                    ui.separator();
                    self.render_graphs(ui);
                }
            }

            // ── Help bar (fundo) ──
            ui.with_layout(egui::Layout::bottom_up(egui::Align::Center), |ui: &mut egui::Ui| {
                ui.label(
                    RichText::new("[F] Fullscreen | [G] Graphs | [T] Theme | [Q/Esc] Quit")
                        .color(self.theme.dim)
                        .monospace()
                        .size(10.0),
                );
            });
        });
    }
}
