# Deploying SaaS Admin Dashboard to Oracle Cloud Always Free

This comprehensive guide walks you through deploying the **SaaS Admin Dashboard** to **Oracle Cloud Infrastructure (OCI)** using an **Always Free** eligible Ubuntu Virtual Machine (VM).

---

## Table of Contents
1. [Architecture Overview on OCI](#1-architecture-overview-on-oci)
2. [Oracle Cloud Always Free VM Selection](#2-oracle-cloud-always-free-vm-selection)
3. [Step 1: Create an Always Free Ubuntu VM](#step-1-create-an-always-free-ubuntu-vm)
4. [Step 2: Configure OCI Virtual Cloud Network (VCN) Ingress Rules](#step-2-configure-oci-virtual-cloud-network-vcn-ingress-rules)
5. [Step 3: Connect to the Server from Windows PowerShell](#step-3-connect-to-the-server-from-windows-powershell)
6. [Step 4: Install Docker & Configure Ubuntu Firewall](#step-4-install-docker--configure-ubuntu-firewall)
7. [Step 5: Clone the Repository & Configure `.env`](#step-5-clone-the-repository--configure-env)
8. [Step 6: Build and Launch the Application](#step-6-build-and-launch-the-application)
9. [Step 7: Run Migrations & Create the Initial Administrator](#step-7-run-migrations--create-the-initial-administrator)
10. [Step 8: Set Up Custom Domain & HTTPS / SSL (Let's Encrypt)](#step-8-set-up-custom-domain--https--ssl-lets-encrypt)
11. [Step 9: Verification Checklist](#step-9-verification-checklist)
12. [Step 10: Maintenance, Backups & Troubleshooting](#step-10-maintenance-backups--troubleshooting)

---

## 1. Architecture Overview on OCI

```
[ Public Internet ]
        │
        ▼ (Port 80 / 443)
┌────────────────────────────────────────────────────────┐
│  OCI Compute Instance (Ubuntu 24.04 LTS)                │
│                                                        │
│   ┌────────────────────────────────────────────────┐   │
│   │ Nginx Reverse Proxy (Container)                 │   │
│   │ - Handles SSL Termination (Let's Encrypt)      │   │
│   │ - Buffering, Gzip, Forwarded Headers           │   │
│   └──────────────────────┬─────────────────────────┘   │
│                          │ internal network: frontend  │
│                          ▼ (Port 8000)                 │
│   ┌────────────────────────────────────────────────┐   │
│   │ FastAPI Application (Uvicorn / Python 3.12)    │   │
│   │ - Non-root user 'app'                          │   │
│   │ - Session cookies, JWT, CSRF validation        │   │
│   └──────────────────────┬─────────────────────────┘   │
│                          │ internal network: backend   │
│                          ▼ (Port 3306 - NOT EXPOSED)   │
│   ┌────────────────────────────────────────────────┐   │
│   │ MySQL 8.0 Database (Container)                 │   │
│   │ - Data persisted in named Docker volume        │   │
│   └────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────┘
```

---

## 2. Oracle Cloud Always Free VM Selection

OCI offers two types of Always Free compute shapes:

| Shape Option | Recommended Shape | Specifications | Always Free Entitlement |
| :--- | :--- | :--- | :--- |
| **Option A (Recommended)** | `VM.Standard.A1.Flex` (Ampere Arm) | **2 to 4 OCPUs, 12 to 24 GB RAM** | Up to 4 OCPUs and 24 GB RAM free per tenancy. Exceptional performance for MySQL + FastAPI. |
| **Option B (Fallback)** | `VM.Standard.E2.1.Micro` (AMD x86_64) | **1/8 OCPU, 1 GB RAM** | 2 instances free per tenancy. Use if Ampere capacity is unavailable in your home region. Set `UVICORN_WORKERS=1`. |

> [!NOTE]
> **Out of Capacity in Region?**
> If OCI returns *"Out of host capacity"* when provisioning the Ampere A1 shape:
> 1. Try reducing to 2 OCPUs and 12 GB RAM.
> 2. Select a different Availability Domain (AD-1, AD-2, AD-3) in the OCI Console.
> 3. Alternatively, deploy on the AMD `VM.Standard.E2.1.Micro` instance (which is always in stock).

---

## Step 1: Create an Always Free Ubuntu VM

1. Log into your [Oracle Cloud Console](https://cloud.oracle.com/).
2. In the navigation menu (top-left ☰), go to **Compute** → **Instances**.
3. Click **Create instance**.
4. Configure the instance settings:
   - **Name:** `saas-admin-dashboard`
   - **Placement:** Keep default Availability Domain.
   - **Image and shape:**
     - Click **Change image** → Select **Canonical Ubuntu** → Choose **Ubuntu 24.04** or **Ubuntu 22.04 Minimal**.
     - Click **Change shape** → Select **Ampere** → Select `VM.Standard.A1.Flex` → Set **2 OCPUs** and **12 GB memory** (or choose `VM.Standard.E2.1.Micro` for AMD).
   - **Networking:**
     - Select **Create new virtual cloud network** (or use existing VCN).
     - Select **Assign a public IPv4 address** (Yes).
   - **Add SSH keys:**
     - Select **Generate a key pair for me** → Click **Save private key** (e.g., save as `oci_key.key` on your Windows PC).
     - *Important:* Keep this file safe; you cannot download it again.
   - **Boot volume:** Leave default (50 GB is Always Free eligible).
5. Click **Create**. The instance status will turn from orange (`PROVISIONING`) to green (`RUNNING`).
6. Copy the **Public IP Address** (e.g. `129.146.x.x`).

---

## Step 2: Configure OCI Virtual Cloud Network (VCN) Ingress Rules

By default, OCI VCNs only permit SSH (port 22). You must allow web traffic:

1. On the Instance details page, click on your **Subnet** link (under *Primary VNIC*).
2. Click on the **Default Security List for...**.
3. Under **Ingress Rules**, click **Add Ingress Rules**.
4. Add the following rules:

#### Ingress Rule for HTTP (Port 80):
- **Source Type:** CIDR
- **Source CIDR:** `0.0.0.0/0`
- **IP Protocol:** TCP
- **Destination Port Range:** `80`
- **Description:** Allow public HTTP traffic for Web and Let's Encrypt

#### Ingress Rule for HTTPS (Port 443):
- **Source Type:** CIDR
- **Source CIDR:** `0.0.0.0/0`
- **IP Protocol:** TCP
- **Destination Port Range:** `443`
- **Description:** Allow public HTTPS traffic

> [!WARNING]
> **Do NOT add port 3306 to Ingress Rules.** Database access is kept strictly internal within the Docker private bridge network.

---

## Step 3: Connect to the Server from Windows PowerShell

Open **Windows PowerShell** on your PC:

1. Set the correct file permissions on your saved SSH private key:
   ```powershell
   icacls "C:\path\to\oci_key.key" /inheritance:r
   icacls "C:\path\to\oci_key.key" /grant:r "$($env:USERNAME):(R)"
   ```

2. Connect via SSH (replace `C:\path\to\oci_key.key` and `YOUR_VM_PUBLIC_IP`):
   ```powershell
   ssh -i "C:\path\to\oci_key.key" ubuntu@YOUR_VM_PUBLIC_IP
   ```

When prompted `Are you sure you want to continue connecting (yes/no/[fingerprint])?`, type `yes` and hit Enter. You are now logged into the Ubuntu VM shell (`ubuntu@saas-admin-dashboard:~$`).

---

## Step 4: Install Docker & Configure Ubuntu Firewall

*(Run these commands inside the Ubuntu VM)*

### 4.1 Update system packages & install prerequisites
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y ca-certificates curl gnupg lsb-release git
```

### 4.2 Install official Docker Engine & Docker Compose
```bash
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Allow running docker without sudo
sudo usermod -aG docker $USER
```

### 4.3 Configure Ubuntu OS Firewall (Critical for OCI!)
Oracle's default Ubuntu images have internal `iptables` rules that block ports 80 and 443 even if the OCI Security List allows them. Run the following to allow web traffic:

```bash
# Allow HTTP and HTTPS in iptables
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT

# Make iptables rules persistent across reboots
sudo apt install -y iptables-persistent
sudo netfilter-persistent save
```

Apply Docker group membership without logging out:
```bash
newgrp docker
```

Verify Docker works:
```bash
docker --version
docker compose version
```

---

## Step 5: Clone the Repository & Configure `.env`

*(Run these commands inside the Ubuntu VM)*

1. Clone your GitHub repository:
   ```bash
   git clone https://github.com/kevinpatel111/saas_admin_dashboard.git
   cd saas_admin_dashboard
   ```

2. Generate cryptographically strong random secrets for production:
   ```bash
   SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))")
   CSRF_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))")
   DB_PASS=$(python3 -c "import secrets; print(secrets.token_hex(16))")
   ROOT_PASS=$(python3 -c "import secrets; print(secrets.token_hex(20))")
   ```

3. Create the production `.env` file:
   ```bash
   cat <<EOF > .env
   APP_NAME="SaaS Admin Dashboard"
   DEBUG=false
   UVICORN_WORKERS=2

   # MySQL Database Credentials
   MYSQL_DATABASE=saas_dashboard
   MYSQL_USER=saas_user
   MYSQL_PASSWORD=${DB_PASS}
   MYSQL_ROOT_PASSWORD=${ROOT_PASS}

   # Security Keys
   SECRET_KEY=${SECRET_KEY}
   CSRF_SECRET=${CSRF_KEY}

   # Cookie security (set to false until HTTPS domain is configured)
   COOKIE_SECURE=false

   # Application business parameters
   ACCESS_TOKEN_EXPIRE_MINUTES=60
   LOW_STOCK_THRESHOLD=10
   ITEMS_PER_PAGE=20
   MAX_LOGIN_ATTEMPTS=5
   LOGIN_LOCKOUT_MINUTES=15
   EOF
   ```

4. Secure the permissions on the `.env` file:
   ```bash
   chmod 600 .env
   ```

---

## Step 6: Build and Launch the Application

*(Run inside the Ubuntu VM in `~/saas_admin_dashboard`)*

Start the full stack (MySQL 8, FastAPI backend, and Nginx reverse proxy):
```bash
docker compose up --build -d
```

Check the health status of all containers:
```bash
docker compose ps
```

You should see:
- `db` status: **healthy**
- `app` status: **healthy**
- `nginx` status: **running**

---

## Step 7: Run Migrations & Create the Initial Administrator

1. Run Alembic schema migrations:
   ```bash
   docker compose exec app alembic upgrade head
   ```

2. Create your secure initial administrator:
   ```bash
   docker compose exec -it app python scripts/create_admin.py
   ```
   Follow the prompts to enter:
   - Admin name: `Your Name`
   - Admin email: `admin@yourdomain.com`
   - Admin password: `ChooseAStrongPassword123!`

3. **Test in your web browser:**
   Open your browser on Windows and navigate to:
   ```text
   http://YOUR_VM_PUBLIC_IP/login
   ```
   Log in with your administrator credentials. You will arrive at the SaaS Dashboard!

---

## Step 8: Set Up Custom Domain & HTTPS / SSL (Let's Encrypt)

When you are ready to bind a custom domain (e.g., `dashboard.mycompany.com`):

1. **Configure DNS:** In your domain DNS registrar (Cloudflare, Namecheap, GoDaddy, Route53, etc.), create an **A Record**:
   - **Type:** `A`
   - **Name:** `dashboard` (or `@`)
   - **Value:** `YOUR_VM_PUBLIC_IP`
   - **TTL:** 5 minutes (or automatic)

2. Run the included automated SSL setup script on the VM:
   ```bash
   bash scripts/setup_ssl.sh dashboard.mycompany.com your-email@example.com
   ```

The script will automatically:
- Obtain an official Let's Encrypt SSL certificate.
- Install the certificate into Nginx.
- Configure automatic HTTP → HTTPS 301 redirection.
- Enable `COOKIE_SECURE=true` in your `.env` so cookies are transmitted strictly over HTTPS.
- Reload Nginx and the application.

3. Access your secured application at `https://dashboard.mycompany.com`.

---

## Step 9: Verification Checklist

| Verification Task | Check Method |
| :--- | :--- |
| **Service Health Check** | `curl -i http://localhost/api/health` returns `200 OK` with `{"status": "ok"}` |
| **Authentication Flow** | Log into `/login`, verify cookie `access_token` and `csrf_token` are set |
| **RBAC Protection** | Staff users cannot access `/users` or create products |
| **Product & Categories** | Create a test category and product, adjust stock quantities |
| **Dashboard Analytics** | Overview cards render correct stats; Chart.js charts load |
| **Reports & CSV Export** | Navigate to `/reports` and download the inventory CSV |
| **Brute-Force Lockout** | 5 consecutive bad passwords on an email trigger a 15-minute lockout |
| **Reboot Survival** | Run `sudo reboot`, reconnect, and verify `docker compose ps` shows services auto-started |

---

## Step 10: Maintenance, Backups & Troubleshooting

### Viewing Live Logs
```bash
# View combined logs
docker compose logs -f

# View only application logs
docker compose logs -f app

# View only Nginx web access / error logs
docker compose logs -f nginx

# View only database logs
docker compose logs -f db
```

### Performing Database Backups
A backup script is included in `scripts/backup_db.sh`:
```bash
bash scripts/backup_db.sh
```
Backups are saved to `backups/saas_backup_YYYYMMDD_HHMMSS.sql.gz`.

#### Set up daily automated backups via Cron:
```bash
crontab -e
```
Add the following line to run daily at 2:00 AM:
```text
0 2 * * * cd /home/ubuntu/saas_admin_dashboard && bash scripts/backup_db.sh >> /home/ubuntu/backup.log 2>&1
```

### Restoring from Backup
```bash
bash scripts/restore_db.sh backups/saas_backup_FILENAME.sql.gz
```

### Updating the Application
When you push code updates to GitHub:
```bash
cd ~/saas_admin_dashboard
git pull origin main
bash scripts/deploy.sh
```

### Common Troubleshooting

#### 1. Cannot open `http://YOUR_VM_PUBLIC_IP` in browser
- **Check OCI Ingress:** Confirm Ingress Rules for port 80 are configured in the VCN Default Security List.
- **Check Ubuntu Firewall:** Run `sudo iptables -L -n -v | grep 80`. If missing, re-run the `iptables` commands from Step 4.3.
- **Check Docker containers:** Run `docker compose ps`. Ensure `nginx` is listening on `0.0.0.0:80`.

#### 2. "Database connection refused" or App restarting
- Check database container health: `docker compose logs db`.
- Verify database credentials in `.env` match:
  `docker compose exec app python -c "from app.config import get_settings; print(get_settings().DATABASE_URL)"`

#### 3. CSRF Verification Failed
- Ensure browser cookies are enabled and you are not opening the site across mixed HTTP/HTTPS origins.
- If accessing via HTTP, ensure `COOKIE_SECURE=false` in `.env`.
