"""
Provider de DNS para AWS Route53.
Implementa a interface DNSProvider usando o boto3 (AWS SDK).
"""

from __future__ import annotations
import logging
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from dns_provider import DNSProvider

logger = logging.getLogger(__name__)


class Route53Provider(DNSProvider):
    """Gerencia registros DNS no AWS Route53 via boto3."""

    def __init__(self, hosted_zone_id: str, aws_access_key_id: str, aws_secret_access_key: str, region: str = 'us-east-1'):
        self.hosted_zone_id = hosted_zone_id
        self.region = region

        logger.debug(f"[Route53] Inicializando provider para Hosted Zone: {hosted_zone_id}")
        self.client = boto3.client(
            'route53',
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region,
        )

    def _ensure_trailing_dot(self, hostname: str) -> str:
        if not hostname.endswith('.'):
            return hostname + '.'
        return hostname

    def _strip_trailing_dot(self, hostname: str) -> str:
        return hostname.rstrip('.')

    def get_zone_info(self) -> dict:
        """Retorna informações da Hosted Zone configurada no Route53."""
        logger.info(f"[Route53] Buscando info da Hosted Zone {self.hosted_zone_id}")
        try:
            response = self.client.get_hosted_zone(Id=self.hosted_zone_id)
            zone = response['HostedZone']
            name = self._strip_trailing_dot(zone.get('Name', ''))
            record_count = zone.get('ResourceRecordSetCount', 0)
            comment = zone.get('Config', {}).get('Comment', '')
            return {
                'name': name,
                'id': zone.get('Id', '').split('/')[-1],
                'status': 'active',
                'record_count': record_count,
                'comment': comment,
            }
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_msg = e.response['Error']['Message']
            logger.error(f"[Route53] Erro ao buscar info da zona ({error_code}): {error_msg}")
            raise RuntimeError(f"Erro Route53 ({error_code}): {error_msg}") from e
        except NoCredentialsError:
            raise RuntimeError("Credenciais AWS inválidas ou não configuradas")

    def list_dns_records(self, record_type: str = 'A') -> list[dict]:
        """Lista todos os registros DNS do tipo informado na Hosted Zone."""
        logger.info(f"[Route53] Listando registros tipo {record_type}")
        result = []

        try:
            paginator = self.client.get_paginator('list_resource_record_sets')
            for page in paginator.paginate(HostedZoneId=self.hosted_zone_id):
                for record in page.get('ResourceRecordSets', []):
                    if record['Type'] == record_type:
                        values = [r['Value'] for r in record.get('ResourceRecords', [])]
                        if values:
                            hostname = self._strip_trailing_dot(record['Name'])
                            logger.debug(f"[Route53] Record: {hostname} -> {values[0]}")
                            result.append({
                                'hostname': hostname,
                                'type': record['Type'],
                                'content': values[0],
                                'ttl': record.get('TTL', 300),
                                'id': hostname,
                            })

            logger.info(f"[Route53] Encontrados {len(result)} registros tipo {record_type}")
            return result

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_msg = e.response['Error']['Message']
            logger.error(f"[Route53] Erro ao listar registros ({error_code}): {error_msg}")
            raise RuntimeError(f"Erro Route53 ({error_code}): {error_msg}") from e
        except NoCredentialsError:
            logger.error("[Route53] Credenciais AWS inválidas ou não configuradas")
            raise RuntimeError("Credenciais AWS inválidas ou não configuradas")

    def get_dns_record(self, hostname: str, record_type: str = 'A') -> dict | None:
        """Busca um registro DNS específico na Hosted Zone do Route53."""
        fqdn = self._ensure_trailing_dot(hostname)

        logger.debug(f"[Route53] Buscando registro: {fqdn} ({record_type})")
        try:
            response = self.client.list_resource_record_sets(
                HostedZoneId=self.hosted_zone_id,
                StartRecordName=fqdn,
                StartRecordType=record_type,
                MaxItems='1',
            )

            for record in response.get('ResourceRecordSets', []):
                if record['Name'] == fqdn and record['Type'] == record_type:
                    values = [r['Value'] for r in record.get('ResourceRecords', [])]
                    if values:
                        ip = values[0]
                        logger.debug(f"[Route53] Registro encontrado: {fqdn} -> {ip}")
                        return {'id': fqdn, 'content': ip}

            logger.debug(f"[Route53] Nenhum registro encontrado para {fqdn}")
            return None

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_msg = e.response['Error']['Message']
            logger.error(f"[Route53] Erro ao buscar registro ({error_code}): {error_msg}")
            raise RuntimeError(f"Erro Route53 ({error_code}): {error_msg}") from e
        except NoCredentialsError:
            logger.error("[Route53] Credenciais AWS inválidas ou não configuradas")
            raise RuntimeError("Credenciais AWS inválidas ou não configuradas")

    def create_dns_record(self, hostname: str, ip_address: str, record_type: str, ttl: int) -> dict:
        """Cria um novo registro DNS no Route53."""
        fqdn = self._ensure_trailing_dot(hostname)

        logger.info(f"[Route53] Criando registro: {fqdn} -> {ip_address} ({record_type}, TTL={ttl})")
        try:
            response = self.client.change_resource_record_sets(
                HostedZoneId=self.hosted_zone_id,
                ChangeBatch={
                    'Comment': f'DynFlask: create {record_type} record for {hostname}',
                    'Changes': [{
                        'Action': 'CREATE',
                        'ResourceRecordSet': {
                            'Name': fqdn,
                            'Type': record_type,
                            'TTL': ttl,
                            'ResourceRecords': [{'Value': ip_address}],
                        }
                    }]
                }
            )

            change_id = response['ChangeInfo']['Id']
            logger.info(f"[Route53] Registro criado — Change ID: {change_id}")
            return {'id': fqdn, 'content': ip_address, 'change_id': change_id}

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_msg = e.response['Error']['Message']
            if error_code == 'InvalidChangeBatch' and 'already exists' in error_msg:
                logger.warning(f"[Route53] Registro já existe, usando UPSERT: {fqdn}")
                return self.update_dns_record(fqdn, hostname, ip_address, record_type, ttl)
            logger.error(f"[Route53] Erro ao criar registro ({error_code}): {error_msg}")
            raise RuntimeError(f"Erro Route53 ({error_code}): {error_msg}") from e

    def update_dns_record(self, record_id: str, hostname: str, ip_address: str, record_type: str, ttl: int) -> dict:
        """Atualiza (UPSERT) um registro DNS no Route53."""
        fqdn = self._ensure_trailing_dot(hostname)

        logger.info(f"[Route53] UPSERT registro: {fqdn} -> {ip_address} ({record_type}, TTL={ttl})")
        try:
            response = self.client.change_resource_record_sets(
                HostedZoneId=self.hosted_zone_id,
                ChangeBatch={
                    'Comment': f'DynFlask: update {record_type} record for {hostname}',
                    'Changes': [{
                        'Action': 'UPSERT',
                        'ResourceRecordSet': {
                            'Name': fqdn,
                            'Type': record_type,
                            'TTL': ttl,
                            'ResourceRecords': [{'Value': ip_address}],
                        }
                    }]
                }
            )

            change_id = response['ChangeInfo']['Id']
            logger.info(f"[Route53] Registro atualizado — Change ID: {change_id}")
            return {'id': fqdn, 'content': ip_address, 'change_id': change_id}

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_msg = e.response['Error']['Message']
            logger.error(f"[Route53] Erro ao atualizar registro ({error_code}): {error_msg}")
            raise RuntimeError(f"Erro Route53 ({error_code}): {error_msg}") from e
        except NoCredentialsError:
            logger.error("[Route53] Credenciais AWS inválidas ou não configuradas")
            raise RuntimeError("Credenciais AWS inválidas ou não configuradas")
