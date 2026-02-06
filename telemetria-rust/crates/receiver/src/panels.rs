//! Painéis individuais de telemetria renderizados com egui.

use crate::theme_egui::EguiTheme;
use egui::{Color32, RichText, Ui};
use telemetry_core::config::AlertThresholds;
use telemetry_core::types::*;

/// Trait para renderizar um painel de componente.
#[allow(dead_code)]
pub trait MetricPanel {
    fn title(&self) -> &str;
    fn accent_color(&self, theme: &EguiTheme) -> Color32;
    fn render(&self, ui: &mut Ui, theme: &EguiTheme, thresholds: &AlertThresholds);
}

// ──────────────────────────────────────────
// Helpers
// ──────────────────────────────────────────

fn metric_row(ui: &mut Ui, label: &str, value: f32, unit: &str, color: Color32, dim: Color32) {
    ui.horizontal(|ui: &mut Ui| {
        ui.label(RichText::new(format!("{label}:")).color(dim).monospace());
        ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui: &mut Ui| {
            let text = format_value(value, unit);
            ui.label(RichText::new(text).color(color).monospace().strong());
        });
    });
}

fn metric_row_string(ui: &mut Ui, label: &str, value: &str, color: Color32, dim: Color32) {
    ui.horizontal(|ui: &mut Ui| {
        ui.label(RichText::new(format!("{label}:")).color(dim).monospace());
        ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui: &mut Ui| {
            ui.label(RichText::new(value).color(color).monospace().strong());
        });
    });
}

fn format_value(value: f32, unit: &str) -> String {
    match unit {
        "V" => format!("{value:.3}{unit}"),
        "°C" | "%" | "W" | " ms" | " RPM" => format!("{value:.1}{unit}"),
        " KB/s" => {
            if value > 1024.0 {
                format!("{:.1} MB/s", value / 1024.0)
            } else {
                format!("{value:.1}{unit}")
            }
        }
        " MHz" => format!("{value:.0}{unit}"),
        " MB" => format!("{value:.0}{unit}"),
        " GB" => format!("{value:.2}{unit}"),
        " Mbps" => format!("{value:.0}{unit}"),
        _ => format!("{value:.1}{unit}"),
    }
}

fn panel_frame(
    ui: &mut Ui,
    title: &str,
    accent: Color32,
    theme: &EguiTheme,
    add_body: impl FnOnce(&mut Ui),
) {
    egui::Frame::new()
        .fill(theme.panel)
        .stroke(egui::Stroke::new(2.0, accent))
        .corner_radius(4.0)
        .inner_margin(8.0)
        .show(ui, |ui: &mut Ui| {
            ui.vertical_centered(|ui: &mut Ui| {
                ui.label(
                    RichText::new(format!("── {title} ──"))
                        .color(accent)
                        .strong()
                        .monospace()
                        .size(13.0),
                );
            });
            ui.add_space(4.0);
            add_body(ui);
        });
}

// ──────────────────────────────────────────
// CPU Panel
// ──────────────────────────────────────────

pub fn render_cpu(ui: &mut Ui, cpu: &CpuData, theme: &EguiTheme, th: &AlertThresholds) {
    panel_frame(ui, "CPU", theme.cpu, theme, |ui: &mut Ui| {
        metric_row(ui, "Uso", cpu.usage, "%", theme.value_color(cpu.usage, th.cpu_usage_warning, th.cpu_usage_critical), theme.dim);
        metric_row(ui, "Temp", cpu.temp, "°C", theme.value_color(cpu.temp, th.cpu_temp_warning, th.cpu_temp_critical), theme.dim);
        metric_row(ui, "Voltagem", cpu.voltage, "V", theme.text, theme.dim);
        metric_row(ui, "Potência", cpu.power, "W", theme.text, theme.dim);
        metric_row(ui, "Clock", cpu.clock, " MHz", theme.text, theme.dim);
    });
}

// ──────────────────────────────────────────
// GPU Panel
// ──────────────────────────────────────────

pub fn render_gpu(ui: &mut Ui, gpu: &GpuData, theme: &EguiTheme, th: &AlertThresholds) {
    panel_frame(ui, "GPU", theme.gpu, theme, |ui: &mut Ui| {
        metric_row(ui, "Uso", gpu.load, "%", theme.value_color(gpu.load, th.gpu_usage_warning, th.gpu_usage_critical), theme.dim);
        metric_row(ui, "Temp", gpu.temp, "°C", theme.value_color(gpu.temp, th.gpu_temp_warning, th.gpu_temp_critical), theme.dim);
        metric_row(ui, "Voltagem", gpu.voltage, "V", theme.text, theme.dim);
        metric_row(ui, "Core", gpu.clock_core, " MHz", theme.text, theme.dim);
        metric_row(ui, "Memória", gpu.clock_mem, " MHz", theme.text, theme.dim);
        metric_row(ui, "Fan", gpu.fan, " RPM", theme.text, theme.dim);
        metric_row(ui, "VRAM", gpu.mem_used_mb, " MB", theme.text, theme.dim);
    });
}

// ──────────────────────────────────────────
// RAM Panel
// ──────────────────────────────────────────

pub fn render_ram(ui: &mut Ui, ram: &RamData, theme: &EguiTheme, th: &AlertThresholds) {
    panel_frame(ui, "RAM", theme.ram, theme, |ui: &mut Ui| {
        metric_row(ui, "Uso", ram.percent, "%", theme.value_color(ram.percent, th.ram_warning, th.ram_critical), theme.dim);
        metric_row(ui, "Usada", ram.used_gb, " GB", theme.text, theme.dim);
        metric_row(ui, "Total", ram.total_gb, " GB", theme.text, theme.dim);
    });
}

// ──────────────────────────────────────────
// Mobo Panel
// ──────────────────────────────────────────

pub fn render_mobo(ui: &mut Ui, mobo: &MoboData, fans: &[FanData], theme: &EguiTheme) {
    panel_frame(ui, "MOBO", theme.mobo, theme, |ui: &mut Ui| {
        metric_row(ui, "Temp", mobo.temp, "°C", theme.text, theme.dim);
        for fan in fans {
            metric_row(ui, &fan.name, fan.rpm, " RPM", theme.text, theme.dim);
        }
    });
}

// ──────────────────────────────────────────
// Storage Panel
// ──────────────────────────────────────────

pub fn render_storage(ui: &mut Ui, storage: &[StorageData], theme: &EguiTheme, th: &AlertThresholds) {
    panel_frame(ui, "STORAGE", theme.storage, theme, |ui: &mut Ui| {
        if storage.is_empty() {
            ui.label(RichText::new("Sem dados").color(theme.dim).monospace());
        }
        for disk in storage {
            // Nome do disco como sub-header
            ui.label(
                RichText::new(&disk.name)
                    .color(theme.storage)
                    .monospace()
                    .size(11.0),
            );
            metric_row(ui, "  Temp", disk.temp, "°C", theme.value_color(disk.temp, th.storage_temp_warning, th.storage_temp_critical), theme.dim);
            metric_row(ui, "  Saúde", disk.health, "%", theme.text, theme.dim);
            metric_row(ui, "  Usado", disk.used_space, "%", theme.value_color(disk.used_space, th.storage_usage_warning, th.storage_usage_critical), theme.dim);
            ui.add_space(2.0);
        }
    });
}

// ──────────────────────────────────────────
// Network Panel
// ──────────────────────────────────────────

pub fn render_network(
    ui: &mut Ui,
    net: &NetworkData,
    theme: &EguiTheme,
    th: &AlertThresholds,
    expected_link: u32,
) {
    panel_frame(ui, "NETWORK", theme.network, theme, |ui: &mut Ui| {
        metric_row(ui, "↓ Down", net.down_kbps, " KB/s", theme.text, theme.dim);
        metric_row(ui, "↑ Up", net.up_kbps, " KB/s", theme.text, theme.dim);
        metric_row(ui, "Ping", net.ping_ms, " ms", theme.value_color(net.ping_ms, th.ping_warning, th.ping_critical), theme.dim);

        // Link speed com alerta se abaixo do esperado
        let link_color = if net.link_speed_mbps > 0 && net.link_speed_mbps < expected_link {
            theme.warning
        } else {
            theme.text
        };
        metric_row(ui, "Link", net.link_speed_mbps as f32, " Mbps", link_color, theme.dim);

        if !net.adapter_name.is_empty() {
            metric_row_string(ui, "Adapter", &net.adapter_name, theme.dim, theme.dim);
        }
    });
}
