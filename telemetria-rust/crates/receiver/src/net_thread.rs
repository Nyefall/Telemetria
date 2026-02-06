//! Thread de rede que escuta UDP e envia payloads para a UI via channel.

use crossbeam_channel::{Receiver, Sender, bounded};
use std::net::UdpSocket;
use telemetry_core::protocol::decode_payload;
use telemetry_core::types::TelemetryPayload;
use tracing::{debug, error, info, warn};

/// Mensagem enviada da thread de rede para a UI.
#[derive(Debug, Clone)]
pub struct NetMessage {
    pub payload: TelemetryPayload,
    pub source_addr: String,
    pub raw_size: usize,
}

/// Inicia a thread de rede. Retorna o receiver do channel.
pub fn spawn_receiver_thread(
    port: u16,
    sender_ip_filter: String,
) -> Receiver<NetMessage> {
    let (tx, rx) = bounded::<NetMessage>(64); // Buffer de 64 mensagens

    std::thread::Builder::new()
        .name("udp-receiver".into())
        .spawn(move || {
            receiver_loop(&tx, port, &sender_ip_filter);
        })
        .expect("Falha ao criar thread de rede");

    rx
}

fn receiver_loop(tx: &Sender<NetMessage>, port: u16, sender_ip_filter: &str) {
    loop {
        match UdpSocket::bind(format!("0.0.0.0:{port}")) {
            Ok(sock) => {
                sock.set_read_timeout(Some(std::time::Duration::from_secs(1)))
                    .ok();

                let mode = if sender_ip_filter.is_empty() {
                    "Auto (broadcast)"
                } else {
                    sender_ip_filter
                };
                info!("Receiver escutando em 0.0.0.0:{port} – Modo: {mode}");

                let mut buf = [0u8; 65536];
                loop {
                    match sock.recv_from(&mut buf) {
                        Ok((size, addr)) => {
                            let source = addr.ip().to_string();

                            // Filtro de IP se configurado
                            if !sender_ip_filter.is_empty() && source != sender_ip_filter {
                                debug!("Ignorando pacote de {source} (esperado: {sender_ip_filter})");
                                continue;
                            }

                            match decode_payload(&buf[..size]) {
                                Ok(payload) => {
                                    let msg = NetMessage {
                                        payload,
                                        source_addr: source,
                                        raw_size: size,
                                    };
                                    // Non-blocking send: se UI está lenta, descarta pacotes antigos
                                    if tx.try_send(msg).is_err() {
                                        debug!("Channel cheio, descartando pacote");
                                    }
                                }
                                Err(e) => {
                                    debug!("Pacote inválido de {source}: {e}");
                                }
                            }
                        }
                        Err(ref e) if e.kind() == std::io::ErrorKind::TimedOut
                            || e.kind() == std::io::ErrorKind::WouldBlock =>
                        {
                            // Timeout normal, continua
                        }
                        Err(e) => {
                            warn!("Erro ao receber UDP: {e}");
                        }
                    }
                }
            }
            Err(e) => {
                error!("Falha ao bind porta {port}: {e}. Tentando novamente em 2s...");
                std::thread::sleep(std::time::Duration::from_secs(2));
            }
        }
    }
}
