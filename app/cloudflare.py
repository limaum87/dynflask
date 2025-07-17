import requests

CLOUDFLARE_API_URL = "https://api.cloudflare.com/client/v4"

def _get_headers(api_token: str) -> dict:
    """Cria os cabeçalhos de autenticação para a API do Cloudflare."""
    return {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }

def get_dns_record(hostname: str, zone_id: str, api_token: str):
    """Busca um registro DNS específico na zona."""
    headers = _get_headers(api_token)
    url = f"{CLOUDFLARE_API_URL}/zones/{zone_id}/dns_records?name={hostname}"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    records = response.json()["result"]
    return records[0] if records else None

def create_dns_record(hostname: str, ip_address: str, record_type: str, ttl: int, zone_id: str, api_token: str):
    """Cria um novo registro DNS."""
    headers = _get_headers(api_token)
    url = f"{CLOUDFLARE_API_URL}/zones/{zone_id}/dns_records"
    data = {
        "type": record_type,
        "name": hostname,
        "content": ip_address,
        "ttl": ttl,
        "proxied": False,
    }
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()["result"]

def update_dns_record(record_id: str, hostname: str, ip_address: str, record_type: str, ttl: int, zone_id: str, api_token: str):
    """Atualiza um registro DNS existente."""
    headers = _get_headers(api_token)
    url = f"{CLOUDFLARE_API_URL}/zones/{zone_id}/dns_records/{record_id}"
    data = {
        "type": record_type,
        "name": hostname,
        "content": ip_address,
        "ttl": ttl,
        "proxied": False,
    }
    response = requests.put(url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()["result"]
