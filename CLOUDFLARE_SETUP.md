# Cloudflare Tunnel Setup for Market Bot

Quick setup for HTTPS access to Mini App.

## Quick Start (2 commands)

```powershell
# 1. Run the setup script
.\scripts\setup-cloudflared-auto.ps1

# 2. Restart bot
docker compose restart bot
```

## Manual Setup

If automatic setup doesn't work:

### Step 1: Install cloudflared

```powershell
winget install cloudflare.cloudflared
```

### Step 2: Start tunnel

**Option A: Use batch file (easiest)**
```cmd
.\scripts\start-cloudflared.bat
```

**Option B: PowerShell**
```powershell
winget exec cloudflare.cloudflared tunnel --url http://localhost:8080
```

### Step 3: Copy URL

You'll see output like:
```
+--------------------------------------------------------------------+
|  Your quick Tunnel has been created!                               |
|                                                                    |
|  It has been assigned the random DNS name:                         |
|  https://a1b2-c3d4-5e6f.trycloudflare.com                          |
+--------------------------------------------------------------------+
```

**Copy the HTTPS URL** (e.g., `https://a1b2-c3d4-5e6f.trycloudflare.com`)

### Step 4: Update .env

Open `.env` and set:
```env
MINI_APP_URL=https://a1b2-c3d4-5e6f.trycloudflare.com/app
```

### Step 5: Restart bot

```bash
docker compose restart bot
```

## Testing

1. Open Telegram
2. Go to @Eliza_rybka_assistant_bot
3. Press /start or "Open Cabinet" button
4. Mini App should open with HTTPS URL

## Important

- **DO NOT CLOSE** the tunnel window while using the bot
- The URL changes each time you restart the tunnel
- For production, use a permanent tunnel with Cloudflare Zero Trust

## Troubleshooting

**"cloudflared: command not found"**
- Install via winget: `winget install cloudflare.cloudflared`
- Or download from: https://github.com/cloudflare/cloudflared/releases

**"Mini App not available on localhost:8080"**
- Start nginx: `docker compose up -d nginx`
- Check: `curl http://localhost:8080/app/`

**"Telegram says only HTTPS allowed"**
- Make sure you're using the full https:// URL from cloudflared
- Don't use http://localhost in production
