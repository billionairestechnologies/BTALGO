# Cloudflare Tunnel Configuration

This directory contains configuration for Cloudflare Tunnel (cloudflared) to securely expose BTALGO without opening firewall ports.

## Setup

1. Install cloudflared
2. Authenticate: `cloudflared tunnel login`
3. Create tunnel: `cloudflared tunnel create btalgo`
4. Update `config.yml` with your tunnel ID and domain
5. Run: `cloudflared tunnel run btalgo`

## Files

- `config.yml` - Tunnel configuration
- `README.md` - This file
