# NutriHealth n8n System (Local + AWS EC2)

This folder contains a complete prototype and deployment path for:

- Self-hosted n8n backend
- Groq + Hugging Face workflow orchestration
- Streamlit UI that calls n8n webhooks

No extra skill was used from `AGENTS.md` because the available skills (`skill-creator`, `skill-installer`) do not match this implementation task.

## Folder Structure

- `docker-compose.local.yml`: local n8n stack
- `.env.local.example`: local environment template
- `workflows/`: importable workflow JSON files
- `ui-streamlit/`: local UI prototype
- `docker-compose.ec2.yml`: production stack for EC2 (n8n + Postgres)
- `.env.ec2.example`: production environment template
- `nginx/n8n.conf`: reverse proxy config for `api.nutihealth.com`
- `scripts/backup-volumes.sh`: backup helper for n8n volume + Postgres dump

---

## 1. Local Development Environment Setup

### 1.1 Install Docker + Docker Compose

If Docker is already installed, skip to **1.2**.

Windows (recommended):

1. Install Docker Desktop:
```powershell
winget install -e --id Docker.DockerDesktop
```
2. Start Docker Desktop once and wait until it shows "Engine running".

macOS:

1. Install Docker Desktop from Docker website or Homebrew:
```bash
brew install --cask docker
```
2. Start Docker Desktop and wait until ready.

Ubuntu/Debian (Linux):

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
newgrp docker
```

Verify install:

```bash
docker --version
docker compose version
```

### 1.2 Start n8n Locally

From this repository root:

PowerShell:

```powershell
cd n8n
Copy-Item .env.local.example .env.local
```

Bash:

```bash
cd n8n
cp .env.local.example .env.local
```

Edit `.env.local` and set real keys:

- `GROQ_API_KEY`
- `HUGGINGFACE_API_KEY`

Start n8n:

```bash
docker compose -f docker-compose.local.yml --env-file .env.local up -d
```

Check logs:

```bash
docker compose -f docker-compose.local.yml logs -f n8n
```

Open n8n UI:

- `http://localhost:5678`

If `N8N_BASIC_AUTH_ACTIVE=true`, login with `N8N_BASIC_AUTH_USER` / `N8N_BASIC_AUTH_PASSWORD`.

---

## 2. Build the n8n Workflows (Locally)

### 2.1 Import the workflow JSON files

Manual intervention required in n8n UI:

1. Open n8n.
2. `Workflows` -> `Import from File`.
3. Import these files:
   - `workflows/workflow-a-ai-meal-planner-groq.json`
   - `workflows/workflow-b-fitness-advice-huggingface.json`
   - `workflows/workflow-c-voice-to-text-whisper.json`
4. Open each workflow and click `Save`.
5. Toggle each workflow to `Active` to enable `/webhook/*` URLs.

### 2.2 Workflow endpoints (local)

When active, your UI should call:

- `http://localhost:5678/webhook/meal-planner`
- `http://localhost:5678/webhook/fitness-advice`
- `http://localhost:5678/webhook/voice-to-text`

Note:

- During manual testing from n8n editor's "Test workflow", n8n can use `webhook-test` paths.
- For real app calls, use `webhook` paths on active workflows.

### 2.3 What each workflow does

Workflow A (`meal-planner`):

- Webhook accepts `diet`, `calories`, `allergies`
- Code node validates input and builds a strict JSON prompt
- AI Agent + Groq model node generates plan
- Code node parses/cleans output to valid JSON
- Respond node returns JSON

Workflow B (`fitness-advice`):

- Webhook accepts `{ "query": "..." }`
- HTTP Request calls Hugging Face Mistral
- Code node parses text response
- Respond node returns `{ ok, advice }`

Workflow C (`voice-to-text`):

- Webhook accepts multipart file field name `data`
- HTTP Request sends audio to Hugging Face Whisper
- Code node extracts transcript
- Respond node returns `{ ok, transcription }`

### 2.4 Credentials setup in n8n UI (manual)

You can run with env vars only (already configured), but production-grade setup should use n8n credentials.

Groq credential (for Workflow A):

1. `Credentials` -> `Add credential` -> `OpenAI API`.
2. Name: `Groq OpenAI Compat`.
3. API key: your Groq key (`gsk_...`).
4. In `Groq Chat Model` node:
   - Select this credential.
   - Keep `baseURL` as `https://api.groq.com/openai/v1`.

Hugging Face credential (for Workflow B/C):

1. `Credentials` -> `Add credential` -> `HTTP Header Auth`.
2. Name: `HuggingFace Header`.
3. Header Name: `Authorization`.
4. Header Value: `Bearer hf_xxx`.
5. In each Hugging Face HTTP Request node:
   - Set Authentication to `Generic Credential Type`.
   - Choose `HTTP Header Auth`.
   - Select `HuggingFace Header`.

### 2.5 Environment variable injection

This stack already injects these env vars into n8n container:

- `GROQ_API_KEY`
- `HUGGINGFACE_API_KEY`

Workflows B/C currently read:

- `{{$env.HUGGINGFACE_API_KEY}}`

If you switch to n8n credentials, you can remove env-var header expressions from those nodes.

---

## 3. Build and Run the Simple UI (Streamlit)

UI source is in `ui-streamlit/`.

### 3.1 Install dependencies

```bash
cd n8n/ui-streamlit
python -m venv .venv
```

PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Bash:

```bash
source .venv/bin/activate
```

Install:

```bash
pip install -r requirements.txt
```

### 3.2 Configure UI env

PowerShell:

```powershell
Copy-Item .env.example .env
```

Bash:

```bash
cp .env.example .env
```

Set:

- `N8N_BASE_URL=http://localhost:5678`
- Optional basic auth values if enabled on n8n

### 3.3 Run UI

```bash
streamlit run app.py
```

Open the shown URL (typically `http://localhost:8501`).

UI features included:

- Meal planner form (diet, calories, allergies)
- Fitness advice text box
- Voice upload for transcription (`wav/mp3/m4a/ogg/flac/webm`)

---

## 4. Local Testing and Verification

Before using UI, test each webhook directly.

If n8n basic auth is enabled, add `-u user:password` in each curl.

### 4.1 Meal planner

```bash
curl -X POST "http://localhost:5678/webhook/meal-planner" \
  -H "Content-Type: application/json" \
  -d "{\"diet\":\"high-protein\",\"calories\":2400,\"allergies\":[\"peanuts\",\"shrimp\"]}"
```

### 4.2 Fitness advice

```bash
curl -X POST "http://localhost:5678/webhook/fitness-advice" \
  -H "Content-Type: application/json" \
  -d "{\"query\":\"Give me a beginner 3-day push pull legs plan\"}"
```

### 4.3 Voice-to-text

```bash
curl -X POST "http://localhost:5678/webhook/voice-to-text" \
  -F "data=@./sample-audio.wav"
```

Windows note: use `curl.exe` explicitly in PowerShell if needed.

### 4.4 End-to-end local verification checklist

1. n8n container is healthy and UI opens.
2. All 3 workflows imported and active.
3. curl calls return valid JSON.
4. Streamlit UI calls each webhook successfully.
5. Groq/HF errors are visible in n8n execution logs for debugging.

---

## 5. AWS EC2 Deployment (n8n Backend)

## 5.1 Launch EC2 instance

Recommended:

- AMI: Amazon Linux 2023
- Instance: `t3.medium`
- Storage: 30+ GB gp3

Security Group inbound:

- `22/tcp` from your IP only
- `80/tcp` from `0.0.0.0/0`
- `443/tcp` from `0.0.0.0/0`

Do not expose `5678` publicly.

### 5.2 Elastic IP and DNS

1. Allocate and attach an Elastic IP to EC2.
2. Create DNS `A` record:
   - `api.nutihealth.com` -> `<elastic-ip>`

Wait until DNS resolves.

### 5.3 Install Docker + Compose on EC2

SSH into server:

```bash
ssh -i /path/to/key.pem ec2-user@<elastic-ip>
```

Install:

```bash
sudo dnf update -y
sudo dnf install -y docker docker-compose-plugin nginx certbot python3-certbot-nginx
sudo systemctl enable --now docker
sudo usermod -aG docker ec2-user
newgrp docker
docker --version
docker compose version
```

### 5.4 Copy deployment files

From local machine:

```bash
ssh -i /path/to/key.pem ec2-user@<elastic-ip> "mkdir -p ~/n8n/workflows ~/n8n/scripts"
```

Then copy files:

```bash
scp -i /path/to/key.pem n8n/docker-compose.ec2.yml ec2-user@<elastic-ip>:~/n8n/
scp -i /path/to/key.pem n8n/.env.ec2.example ec2-user@<elastic-ip>:~/n8n/.env.ec2
scp -i /path/to/key.pem n8n/nginx/n8n.conf ec2-user@<elastic-ip>:~/n8n/n8n.conf
scp -i /path/to/key.pem n8n/workflows/*.json ec2-user@<elastic-ip>:~/n8n/workflows/
scp -i /path/to/key.pem n8n/scripts/backup-volumes.sh ec2-user@<elastic-ip>:~/n8n/scripts/
```

On EC2:

```bash
cd ~/n8n
```

Edit `~/n8n/.env.ec2`:

- set strong `N8N_BASIC_AUTH_PASSWORD`
- set `POSTGRES_PASSWORD`
- set `GROQ_API_KEY`, `HUGGINGFACE_API_KEY`
- confirm `N8N_HOST=api.nutihealth.com`
- confirm `WEBHOOK_URL=https://api.nutihealth.com/`

### 5.5 Start n8n stack on EC2

```bash
cd ~/n8n
docker compose -f docker-compose.ec2.yml --env-file .env.ec2 up -d
docker compose -f docker-compose.ec2.yml ps
```

### 5.6 Configure Nginx reverse proxy

Install config:

```bash
sudo cp ~/n8n/n8n.conf /etc/nginx/conf.d/n8n.conf
sudo nginx -t
sudo systemctl enable --now nginx
sudo systemctl reload nginx
```

### 5.7 Enable HTTPS with Let's Encrypt

```bash
sudo certbot --nginx -d api.nutihealth.com --agree-tos -m you@example.com --redirect -n
```

Test:

- `https://api.nutihealth.com`

### 5.8 Import workflows into production n8n

Manual UI method:

1. Open `https://api.nutihealth.com`.
2. Login with n8n basic auth.
3. Import the same three JSON files from `~/n8n/workflows`.
4. Re-select credentials in nodes if needed.
5. Activate workflows.

Alternative:

- Export/import through n8n UI from local to prod.

### 5.9 Update UI to production URL

In Streamlit `.env`:

```env
N8N_BASE_URL=https://api.nutihealth.com
```

Or set it in sidebar input at runtime.

---

## 6. Post-Deployment Considerations

### 6.1 Backup strategy

Use included script (on EC2):

```bash
cd ~/n8n
chmod +x scripts/backup-volumes.sh
POSTGRES_USER=n8n POSTGRES_DB=n8n ./scripts/backup-volumes.sh ./backups
```

What it backs up:

- `n8n_data` Docker volume
- Postgres SQL dump (if DB container exists)

Recommendation:

- Run daily via cron
- Sync backup files to S3 bucket

### 6.2 Monitoring/logging

Basic:

```bash
docker compose -f docker-compose.ec2.yml logs -f n8n
docker compose -f docker-compose.ec2.yml logs -f postgres
docker stats
```

Recommended:

- CloudWatch Agent for host metrics
- Centralized container logs
- Uptime checks on `https://api.nutihealth.com/healthz` (if you add health endpoint workflow)

### 6.3 Security best practices

- Keep `5678` bound to localhost only (already configured).
- Keep SSH limited to your IP.
- Use strong basic-auth password and rotate regularly.
- Rotate Groq/Hugging Face keys regularly.
- Keep Amazon Linux and Docker images updated.
- Restrict who can access n8n UI.
- Prefer n8n Credentials over plain env vars for API secrets.

---

## 7. Summary Checklist

- [ ] Docker + Docker Compose installed locally
- [ ] `n8n/.env.local` created and API keys set
- [ ] Local n8n started (`docker-compose.local.yml`)
- [ ] 3 workflow JSON files imported and activated
- [ ] Groq + Hugging Face credentials configured in n8n UI
- [ ] Streamlit UI installed and running locally
- [ ] curl tests pass for all 3 webhooks
- [ ] EC2 launched with correct Security Group
- [ ] Elastic IP attached and DNS `api.nutihealth.com` configured
- [ ] `docker-compose.ec2.yml` + `.env.ec2` deployed to EC2
- [ ] Nginx reverse proxy configured
- [ ] Let's Encrypt SSL issued and auto-renew works
- [ ] Workflows imported into production n8n and activated
- [ ] UI base URL switched to production
- [ ] Backups + monitoring + key rotation process in place
