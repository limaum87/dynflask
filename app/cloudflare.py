"""
Provider de DNS para Cloudflare.
Implementa a interface DNSProvider usando a API REST do Cloudflare.
"""

from __future__ import annotations
import logging
import requests
from dns_provider import DNSProvider

logger = logging.getLogger(__name__)

CLOUDFLARE_API_URL = "https://api.cloudflare.com/client/v4"


class CloudflareProvider(DNSProvider):
    """Gerencia registros DNS no Cloudflare via API REST."""

    def __init__(self, zone_id: str, api_token: str):
        self.zone_id = zone_id
        self.api_token = api_token

    def _get_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

    def get_zone_info(self) -> dict:
        """Retorna informações da zona configurada no Cloudflare."""
        headers = self._get_headers()
        url = f"{CLOUDFLARE_API_URL}/zones/{self.zone_id}"

        logger.info(f"[Cloudflare] Buscando info da zona {self.zone_id}")
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        result = response.json()["result"]
        return {
            'name': result.get('name', ''),
            'id': result.get('id', ''),
            'status': result.get('status', ''),
            'record_count': result.get('meta', {}).get('custom_certificate_quota', 0),
        }

    def list_dns_records(self, record_type: str = 'A') -> list[dict]:
        """Lista todos os registros DNS do tipo informado na zona do Cloudflare."""
        headers = self._get_headers()
        url = f"{CLOUDFLARE_API_URL}/zones/{self.zone_id}/dns_records?type={record_type}&per_page=5000"

        logger.info(f"[Cloudflare] Listando registros tipo {record_type}")
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        records = response.json()["result"]
        result = []
        for r in records:
            result.append({
                'hostname': r['name'],
                'type': r['type'],
                'content': r['content'],
                'ttl': r['ttl'],
                'id': r['id'],
            })
        logger.info(f"[Cloudflare] Encontrados {len(result)} registros tipo {record_type}")
        return result

    def get_dns_record(self, hostname: str, record_type: str = 'A') -> dict | None:
        """Busca um registro DNS específico na zona do Cloudflare."""
        headers = self._get_headers()
        url = f"{CLOUDFLARE_API_URL}/zones/{self.zone_id}/dns_records?name={hostname}&type={record_type}"

        logger.debug(f"[Cloudflare] Buscando registro: {hostname} ({record_type})")
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        records = response.json()["result"]
        if records:
            record = records[0]
            logger.debug(f"[Cloudflare] Registro encontrado: {record['id']} -> {record['content']}")
            return {'id': record['id'], 'content': record['content']}

        logger.debug(f"[Cloudflare] Nenhum registro encontrado para {hostname}")
        return None

    def create_dns_record(self, hostname: str, ip_address: str, record_type: str, ttl: int) -> dict:
        """Cria um novo registro DNS no Cloudflare."""
        headers = self._get_headers()
        url = f"{CLOUDFLARE_API_URL}/zones/{self.zone_id}/dns_records"
        data = {
            "type": record_type,
            "name": hostname,
            "content": ip_address,
            "ttl": ttl,
            "proxied": False,
        }

        logger.info(f"[Cloudflare] Criando registro: {hostname} -> {ip_address} ({record_type}, TTL={ttl})")
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()

        result = response.json()["result"]
        logger.info(f"[Cloudflare] Registro criado com ID: {result['id']}")
        return result

    def update_dns_record(self, record_id: str, hostname: str, ip_address: str, record_type: str, ttl: int) -> dict:
        """Atualiza um registro DNS existente no Cloudflare."""
        headers = self._get_headers()
        url = f"{CLOUDFLARE_API_URL}/zones/{self.zone_id}/dns_records/{record_id}"
        data = {
            "type": record_type,
            "name": hostname,
            "content": ip_address,
            "ttl": ttl,
            "proxied": False,
        }

        logger.info(f"[Cloudflare] Atualizando registro {record_id}: {hostname} -> {ip_address}")
        response = requests.put(url, headers=headers, json=data)
        response.raise_for_status()

        result = response.json()["result"]
        logger.info(f"[Cloudflare] Registro {record_id} atualizado com sucesso")
        return result
