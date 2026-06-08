"""
Fábrica de providers de DNS.
Retorna a instância correta do provider com base no nome e nas credenciais do banco.
"""

from __future__ import annotations
import logging
from cloudflare import CloudflareProvider
from route53_provider import Route53Provider
from models import Setting
from security import decrypt_value

logger = logging.getLogger(__name__)


class ProviderNotFoundError(Exception):
    """Levantada quando o provider solicitado não existe."""
    pass


class ProviderNotConfiguredError(Exception):
    """Levantada quando as credenciais do provider não estão configuradas."""
    pass


def get_provider(provider_name: str) -> CloudflareProvider | Route53Provider:
    """
    Cria e retorna uma instância do provider de DNS solicitado.

    Args:
        provider_name: Nome do provider ('cloudflare' ou 'route53').

    Returns:
        Instância de DNSProvider configurada.

    Raises:
        ProviderNotFoundError: Se o provider não é suportado.
        ProviderNotConfiguredError: Se as credenciais não estão no banco.
    """
    if provider_name == 'cloudflare':
        return _get_cloudflare_provider()
    elif provider_name == 'route53':
        return _get_route53_provider()
    else:
        raise ProviderNotFoundError(f"Provider desconhecido: '{provider_name}'. Use 'cloudflare' ou 'route53'.")


def _get_cloudflare_provider() -> CloudflareProvider:
    """Cria instância do CloudflareProvider com credenciais do banco."""
    zone_id_setting = Setting.query.filter_by(key='CLOUDFLARE_ZONE_ID').first()
    api_token_setting = Setting.query.filter_by(key='CLOUDFLARE_API_TOKEN').first()

    if not zone_id_setting or not zone_id_setting.value:
        raise ProviderNotConfiguredError(
            "Credenciais do Cloudflare não configuradas. "
            "Acesse Configurações e defina o Zone ID e API Token."
        )

    if not api_token_setting or not api_token_setting.value:
        raise ProviderNotConfiguredError(
            "Credenciais do Cloudflare não configuradas. "
            "Acesse Configurações e defina o API Token."
        )

    zone_id = zone_id_setting.value
    api_token = decrypt_value(api_token_setting.value)

    logger.debug(f"[Factory] Instanciando CloudflareProvider (zone: {zone_id[:8]}...)")
    return CloudflareProvider(zone_id=zone_id, api_token=api_token)


def _get_route53_provider() -> Route53Provider:
    """Cria instância do Route53Provider com credenciais do banco."""
    zone_id_setting = Setting.query.filter_by(key='ROUTE53_HOSTED_ZONE_ID').first()
    access_key_setting = Setting.query.filter_by(key='ROUTE53_AWS_ACCESS_KEY_ID').first()
    secret_key_setting = Setting.query.filter_by(key='ROUTE53_AWS_SECRET_ACCESS_KEY').first()
    region_setting = Setting.query.filter_by(key='ROUTE53_AWS_REGION').first()

    if not zone_id_setting or not zone_id_setting.value:
        raise ProviderNotConfiguredError(
            "Credenciais do Route53 não configuradas. "
            "Acesse Configurações e defina o Hosted Zone ID."
        )

    if not access_key_setting or not access_key_setting.value:
        raise ProviderNotConfiguredError(
            "Credenciais do Route53 não configuradas. "
            "Acesse Configurações e defina o AWS Access Key ID."
        )

    if not secret_key_setting or not secret_key_setting.value:
        raise ProviderNotConfiguredError(
            "Credenciais do Route53 não configuradas. "
            "Acesse Configurações e defina o AWS Secret Access Key."
        )

    hosted_zone_id = zone_id_setting.value
    access_key = access_key_setting.value
    secret_key = decrypt_value(secret_key_setting.value)
    region = region_setting.value if region_setting else 'us-east-1'

    logger.debug(f"[Factory] Instanciando Route53Provider (zone: {hosted_zone_id}, region: {region})")
    return Route53Provider(
        hosted_zone_id=hosted_zone_id,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region=region,
    )


def get_configured_providers() -> list[str]:
    """
    Retorna lista de nomes de providers que possuem credenciais configuradas.
    Útil para validar formulários e exibir status na interface.
    """
    configured = []

    # Cloudflare
    cf_zone = Setting.query.filter_by(key='CLOUDFLARE_ZONE_ID').first()
    cf_token = Setting.query.filter_by(key='CLOUDFLARE_API_TOKEN').first()
    if cf_zone and cf_zone.value and cf_token and cf_token.value:
        configured.append('cloudflare')

    # Route53
    r53_zone = Setting.query.filter_by(key='ROUTE53_HOSTED_ZONE_ID').first()
    r53_access = Setting.query.filter_by(key='ROUTE53_AWS_ACCESS_KEY_ID').first()
    r53_secret = Setting.query.filter_by(key='ROUTE53_AWS_SECRET_ACCESS_KEY').first()
    if r53_zone and r53_zone.value and r53_access and r53_access.value and r53_secret and r53_secret.value:
        configured.append('route53')

    return configured
