"""
Interface abstrata para providers de DNS.
Todos os providers (Cloudflare, Route53, etc.) devem implementar esta interface.
"""

from __future__ import annotations
from abc import ABC, abstractmethod


class DNSProvider(ABC):
    """Classe abstrata que define o contrato para provedores de DNS."""

    @abstractmethod
    def get_zone_info(self) -> dict:
        """
        Retorna informações da zona configurada no provider.

        Returns:
            dict com pelo menos:
            - 'name': str (nome real da zona, ex: 'accept.inf.br')
            - 'id': str (ID da zona no provider)
            - 'record_count': int (total de registros, se disponível)
        """
        ...

    @abstractmethod
    def list_dns_records(self, record_type: str = 'A') -> list[dict]:
        """
        Lista todos os registros DNS da zona para um dado tipo.

        Args:
            record_type: Tipo do registro (A, AAAA, CNAME, etc.).

        Returns:
            Lista de dicts, cada um com pelo menos:
            - 'hostname': str (FQDN)
            - 'type': str
            - 'content': str (IP ou valor)
            - 'ttl': int
        """
        ...

    @abstractmethod
    def get_dns_record(self, hostname: str, record_type: str = 'A') -> dict | None:
        """
        Busca um registro DNS existente.

        Args:
            hostname: O nome do host completo (ex: home.example.com).
            record_type: Tipo do registro DNS (A, AAAA, etc.).

        Returns:
            dict com pelo menos {'id': str, 'content': str} ou None se não encontrado.
        """
        ...

    @abstractmethod
    def create_dns_record(self, hostname: str, ip_address: str, record_type: str, ttl: int) -> dict:
        """
        Cria um novo registro DNS.

        Args:
            hostname: O nome do host completo.
            ip_address: O endereço IP para o registro.
            record_type: Tipo do registro (A, AAAA).
            ttl: Time-to-live em segundos.

        Returns:
            dict com os dados do registro criado.
        """
        ...

    @abstractmethod
    def update_dns_record(self, record_id: str, hostname: str, ip_address: str, record_type: str, ttl: int) -> dict:
        """
        Atualiza um registro DNS existente.

        Args:
            record_id: Identificador único do registro no provider.
            hostname: O nome do host completo.
            ip_address: O novo endereço IP.
            record_type: Tipo do registro (A, AAAA).
            ttl: Time-to-live em segundos.

        Returns:
            dict com os dados do registro atualizado.
        """
        ...

    def upsert_dns_record(self, hostname: str, ip_address: str, record_type: str, ttl: int) -> dict:
        """
        Cria ou atualiza um registro DNS (conveniência).

        Returns:
            dict com {'action': 'created'|'updated'|'noop', 'record': dict}
        """
        record = self.get_dns_record(hostname, record_type)

        if record:
            if record.get('content') == ip_address:
                return {'action': 'noop', 'record': record}
            self.update_dns_record(record['id'], hostname, ip_address, record_type, ttl)
            return {'action': 'updated', 'record': record}
        else:
            new_record = self.create_dns_record(hostname, ip_address, record_type, ttl)
            return {'action': 'created', 'record': new_record}
