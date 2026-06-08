-- Migration: Adicionar suporte a múltiplos DNS providers
-- Data: 2026-06-08

-- Adiciona coluna 'provider' na tabela hosts
ALTER TABLE hosts ADD COLUMN provider VARCHAR(50) NOT NULL DEFAULT 'cloudflare' AFTER auth_token;
