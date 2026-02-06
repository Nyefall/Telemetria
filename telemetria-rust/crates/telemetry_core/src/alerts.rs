//! Sistema de alertas – níveis e avaliação de thresholds.

use crate::config::AlertThresholds;
use crate::types::TelemetryPayload;
use serde::{Deserialize, Serialize};

/// Nível de alerta.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
pub enum AlertLevel {
    Normal,
    Warning,
    Critical,
}

/// Um alerta disparado.
#[derive(Debug, Clone)]
pub struct Alert {
    pub metric: String,
    pub label: String,
    pub value: f32,
    pub unit: String,
    pub level: AlertLevel,
}

/// Avalia um payload contra os thresholds e retorna alertas.
pub fn evaluate_alerts(payload: &TelemetryPayload, thresholds: &AlertThresholds) -> Vec<Alert> {
    let mut alerts = Vec::new();

    // CPU Temp
    check(
        &mut alerts,
        "cpu_temp",
        "CPU Temp",
        payload.cpu.temp,
        "°C",
        thresholds.cpu_temp_warning,
        thresholds.cpu_temp_critical,
    );

    // CPU Usage
    check(
        &mut alerts,
        "cpu_usage",
        "CPU Uso",
        payload.cpu.usage,
        "%",
        thresholds.cpu_usage_warning,
        thresholds.cpu_usage_critical,
    );

    // GPU Temp
    check(
        &mut alerts,
        "gpu_temp",
        "GPU Temp",
        payload.gpu.temp,
        "°C",
        thresholds.gpu_temp_warning,
        thresholds.gpu_temp_critical,
    );

    // GPU Load
    check(
        &mut alerts,
        "gpu_usage",
        "GPU Uso",
        payload.gpu.load,
        "%",
        thresholds.gpu_usage_warning,
        thresholds.gpu_usage_critical,
    );

    // RAM
    check(
        &mut alerts,
        "ram",
        "RAM",
        payload.ram.percent,
        "%",
        thresholds.ram_warning,
        thresholds.ram_critical,
    );

    // Ping
    check(
        &mut alerts,
        "ping",
        "Ping",
        payload.network.ping_ms,
        "ms",
        thresholds.ping_warning,
        thresholds.ping_critical,
    );

    // Storage
    for (i, disk) in payload.storage.iter().enumerate() {
        check(
            &mut alerts,
            &format!("storage_{i}_temp"),
            &format!("{} Temp", disk.name),
            disk.temp,
            "°C",
            thresholds.storage_temp_warning,
            thresholds.storage_temp_critical,
        );
        check(
            &mut alerts,
            &format!("storage_{i}_usage"),
            &format!("{} Uso", disk.name),
            disk.used_space,
            "%",
            thresholds.storage_usage_warning,
            thresholds.storage_usage_critical,
        );
    }

    alerts
}

fn check(
    alerts: &mut Vec<Alert>,
    metric: &str,
    label: &str,
    value: f32,
    unit: &str,
    warn: f32,
    crit: f32,
) {
    if value <= 0.0 {
        return; // Sensor não disponível
    }
    let level = if value >= crit {
        AlertLevel::Critical
    } else if value >= warn {
        AlertLevel::Warning
    } else {
        return; // Normal, não gera alerta
    };

    alerts.push(Alert {
        metric: metric.into(),
        label: label.into(),
        value,
        unit: unit.into(),
        level,
    });
}

/// Retorna o [`AlertLevel`] para um valor dado thresholds.
pub fn level_for_value(value: f32, warn: f32, crit: f32) -> AlertLevel {
    if value >= crit {
        AlertLevel::Critical
    } else if value >= warn {
        AlertLevel::Warning
    } else {
        AlertLevel::Normal
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::config::AlertThresholds;
    use crate::types::*;

    #[test]
    fn no_alerts_for_normal_values() {
        let payload = TelemetryPayload {
            cpu: CpuData {
                usage: 30.0,
                temp: 50.0,
                ..Default::default()
            },
            ..Default::default()
        };
        let thresholds = AlertThresholds::default();
        let alerts = evaluate_alerts(&payload, &thresholds);
        assert!(alerts.is_empty());
    }

    #[test]
    fn critical_cpu_temp_triggers_alert() {
        let payload = TelemetryPayload {
            cpu: CpuData {
                temp: 95.0,
                ..Default::default()
            },
            ..Default::default()
        };
        let thresholds = AlertThresholds::default();
        let alerts = evaluate_alerts(&payload, &thresholds);
        assert!(!alerts.is_empty());
        assert_eq!(alerts[0].level, AlertLevel::Critical);
        assert_eq!(alerts[0].metric, "cpu_temp");
    }

    #[test]
    fn warning_level() {
        assert_eq!(level_for_value(75.0, 70.0, 85.0), AlertLevel::Warning);
        assert_eq!(level_for_value(90.0, 70.0, 85.0), AlertLevel::Critical);
        assert_eq!(level_for_value(50.0, 70.0, 85.0), AlertLevel::Normal);
    }
}
