"""
Protocolo de comunicação do Sistema de Telemetria
Define o formato de mensagens e compressão
"""
import gzip
import json
from enum import IntEnum
from typing import Any, Optional


class MagicByte(IntEnum):
    """Magic bytes para identificar tipo de payload"""
    RAW = 0x00      # JSON sem compressão
    GZIP = 0x01     # JSON comprimido com gzip
    
    # Reservados para futuras expansões
    MSGPACK = 0x02  # MessagePack (futuro)
    PROTOBUF = 0x03 # Protocol Buffers (futuro)


def encode_payload(
    data: dict[str, Any], 
    compress: bool = True,
    compression_level: int = 6
) -> bytes:
    """
    Codifica payload para transmissão
    
    Args:
        data: Dicionário com dados de telemetria
        compress: Se True, comprime com gzip
        compression_level: Nível de compressão (1-9)
    
    Returns:
        Bytes prontos para envio via socket
    """
    json_data = json.dumps(data, separators=(',', ':')).encode('utf-8')
    
    if compress:
        compressed = gzip.compress(json_data, compresslevel=compression_level)
        return bytes([MagicByte.GZIP]) + compressed
    
    return bytes([MagicByte.RAW]) + json_data


def decode_payload(data: bytes) -> Optional[dict[str, Any]]:
    """
    Decodifica payload recebido
    
    Args:
        data: Bytes recebidos via socket
    
    Returns:
        Dicionário com dados ou None se inválido
    """
    if not data or len(data) < 2:
        return None
    
    try:
        magic = data[0]
        payload_data = data[1:]
        
        if magic == MagicByte.GZIP:
            json_data = gzip.decompress(payload_data)
        elif magic == MagicByte.RAW:
            json_data = payload_data
        else:
            # Retrocompatibilidade: sem magic byte
            # Tenta gzip primeiro, depois raw
            try:
                json_data = gzip.decompress(data)
            except (gzip.BadGzipFile, OSError):
                json_data = data
        
        return json.loads(json_data.decode('utf-8'))
    
    except (json.JSONDecodeError, gzip.BadGzipFile, OSError, UnicodeDecodeError) as e:
        print(f"[Protocol] Erro ao decodificar payload: {e}")
        return None


def get_payload_stats(data: dict[str, Any]) -> dict[str, int | float]:
    """
    Retorna estatísticas do payload para debug
    
    Args:
        data: Dicionário com dados
    
    Returns:
        Dict com tamanho raw, comprimido e ratio
    """
    raw = encode_payload(data, compress=False)
    compressed = encode_payload(data, compress=True)
    
    return {
        "raw_size": len(raw),
        "compressed_size": len(compressed),
        "compression_ratio": round((1 - len(compressed) / len(raw)) * 100, 1)
    }
