#!/bin/bash
# ============================================================
#  Vertex Coders LLC — HTB Machine Setup Script
#  Version: 1.0.0
#  Author: Denis Sanchez Leyva
#
#  Usage:
#    sudo bash vtx-setup.sh --name NexusAI \
#                           --difficulty hard \
#                           --user nexus \
#                           --password N3xusSuperS3cr3t! \
#                           --port 1337 \
#                           --repo https://github.com/Denisijcu/nexusai.git \
#                           --privesc cron
# ============================================================

set -e

# ── COLORS ────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ── LOGGING ───────────────────────────────────────────────
log()     { echo -e "${GREEN}[+]${NC} $1"; }
warn()    { echo -e "${YELLOW}[!]${NC} $1"; }
error()   { echo -e "${RED}[✗]${NC} $1"; exit 1; }
section() { echo -e "\n${CYAN}${BOLD}━━━ $1 ━━━${NC}"; }

# ── ROOT CHECK ────────────────────────────────────────────
if [ "$EUID" -ne 0 ]; then
    error "Run as root: sudo bash $0"
fi

# ── DEFAULTS ──────────────────────────────────────────────
MACHINE_NAME=""
DIFFICULTY=""
USERNAME=""
USER_PASSWORD=""
APP_PORT=""
REPO_URL=""
PRIVESC_TYPE=""
APP_ENTRY="app.py"
SKIP_DOCKER=false

# ── PARSE ARGUMENTS ───────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case $1 in
        --name)        MACHINE_NAME="$2";  shift 2 ;;
        --difficulty)  DIFFICULTY="$2";    shift 2 ;;
        --user)        USERNAME="$2";      shift 2 ;;
        --password)    USER_PASSWORD="$2"; shift 2 ;;
        --port)        APP_PORT="$2";      shift 2 ;;
        --repo)        REPO_URL="$2";      shift 2 ;;
        --privesc)     PRIVESC_TYPE="$2";  shift 2 ;;
        --entry)       APP_ENTRY="$2";     shift 2 ;;
        --skip-docker) SKIP_DOCKER=true;   shift ;;
        --help)
            echo ""
            echo "  Vertex Coders LLC — HTB Machine Setup"
            echo ""
            echo "  Usage: sudo bash vtx-setup.sh [OPTIONS]"
            echo ""
            echo "  Required:"
            echo "    --name        Machine name (e.g. NexusAI)"
            echo "    --difficulty  easy | medium | hard"
            echo "    --user        Linux username for the machine"
            echo "    --password    User password"
            echo "    --port        App port (e.g. 1337)"
            echo "    --repo        GitHub repo URL"
            echo "    --privesc     sudo | cron | suid | capabilities"
            echo ""
            echo "  Optional:"
            echo "    --entry       App entry point (default: app.py)"
            echo "    --skip-docker Skip Docker cleanup step"
            echo ""
            echo "  Example:"
            echo "    sudo bash vtx-setup.sh \\"
            echo "      --name NexusAI \\"
            echo "      --difficulty hard \\"
            echo "      --user nexus \\"
            echo "      --password N3xusSuperS3cr3t! \\"
            echo "      --port 1337 \\"
            echo "      --repo https://github.com/Denisijcu/nexusai.git \\"
            echo "      --privesc cron"
            echo ""
            exit 0
            ;;
        *) error "Unknown option: $1. Use --help for usage." ;;
    esac
done

# ── VALIDATE REQUIRED ARGS ────────────────────────────────
[ -z "$MACHINE_NAME" ]  && error "Missing --name"
[ -z "$DIFFICULTY" ]    && error "Missing --difficulty"
[ -z "$USERNAME" ]      && error "Missing --user"
[ -z "$USER_PASSWORD" ] && error "Missing --password"
[ -z "$APP_PORT" ]      && error "Missing --port"
[ -z "$REPO_URL" ]      && error "Missing --repo"
[ -z "$PRIVESC_TYPE" ]  && error "Missing --privesc"

MACHINE_LOWER=$(echo "$MACHINE_NAME" | tr '[:upper:]' '[:lower:]')
APP_DIR="/opt/$MACHINE_LOWER"

# ── BANNER ────────────────────────────────────────────────
echo ""
echo -e "${CYAN}${BOLD}"
echo "  ╦  ╦╔═╗╦═╗╔╦╗╔═╗╦ ╦  ╔═╗╔═╗╔╦╗╔═╗╦═╗╔═╗"
echo "  ╚╗╔╝║╣ ╠╦╝ ║ ║╣ ╚╦╝  ║  ║ ║ ║║║╣ ╠╦╝╚═╗"
echo "   ╚╝ ╚═╝╩╚═ ╩ ╚═╝ ╩   ╚═╝╚═╝═╩╝╚═╝╩╚═╚═╝"
echo -e "  HTB Machine Setup v1.0.0${NC}"
echo ""
echo -e "  Machine:    ${BOLD}$MACHINE_NAME${NC} ($DIFFICULTY)"
echo -e "  User:       ${BOLD}$USERNAME${NC}"
echo -e "  Port:       ${BOLD}$APP_PORT${NC}"
echo -e "  PrivEsc:    ${BOLD}$PRIVESC_TYPE${NC}"
echo -e "  Repo:       ${BOLD}$REPO_URL${NC}"
echo ""
read -p "  Continue? [y/N] " -n 1 -r
echo ""
[[ ! $REPLY =~ ^[Yy]$ ]] && echo "Aborted." && exit 0

# ── LOG FILE ──────────────────────────────────────────────
LOGFILE="/var/log/vtx-setup-$MACHINE_LOWER.log"
exec > >(tee -a "$LOGFILE") 2>&1
log "Logging to $LOGFILE"

# ── STEP 0: DOCKER CLEANUP ────────────────────────────────
section "STEP 0 — Docker Cleanup"
if [ "$SKIP_DOCKER" = false ]; then
    if command -v docker &>/dev/null; then
        CONTAINERS=$(docker ps -aq 2>/dev/null)
        if [ -n "$CONTAINERS" ]; then
            log "Stopping containers..."
            docker stop $CONTAINERS 2>/dev/null || true
            docker rm $CONTAINERS 2>/dev/null || true
            log "Containers removed"
        else
            log "No containers running"
        fi
        IMAGES=$(docker images -q 2>/dev/null)
        if [ -n "$IMAGES" ]; then
            docker rmi $IMAGES 2>/dev/null || true
            log "Docker images removed"
        fi
    else
        warn "Docker not installed — skipping"
    fi
else
    warn "Skipping Docker cleanup (--skip-docker)"
fi

# ── STEP 1: HOSTNAME ──────────────────────────────────────
section "STEP 1 — Hostname"
OLD_HOSTNAME=$(hostname)
hostnamectl set-hostname "$MACHINE_LOWER"
echo "$MACHINE_LOWER" > /etc/hostname
sed -i "s/$OLD_HOSTNAME/$MACHINE_LOWER/g" /etc/hosts
log "Hostname set to: $MACHINE_LOWER"

# ── STEP 2: CLEAN OLD USERS ───────────────────────────────
section "STEP 2 — User Management"
OLD_USERS=("htbuser" "aria" "nexus" "www-data-htb")
for OLD_USER in "${OLD_USERS[@]}"; do
    if id "$OLD_USER" &>/dev/null && [ "$OLD_USER" != "$USERNAME" ]; then
        pkill -u "$OLD_USER" 2>/dev/null || true
        sleep 1
        userdel -r "$OLD_USER" 2>/dev/null || true
        log "Removed old user: $OLD_USER"
    fi
done

# Create new user
if id "$USERNAME" &>/dev/null; then
    warn "User $USERNAME already exists — updating password"
    echo "$USERNAME:$USER_PASSWORD" | chpasswd
else
    useradd -m -s /bin/bash "$USERNAME"
    echo "$USERNAME:$USER_PASSWORD" | chpasswd
    log "Created user: $USERNAME"
fi

# ── STEP 3: SSH KEYS ──────────────────────────────────────
section "STEP 3 — SSH Keys"
SSH_DIR="/home/$USERNAME/.ssh"
mkdir -p "$SSH_DIR"

if [ ! -f "$SSH_DIR/id_rsa" ]; then
    ssh-keygen -t rsa -b 2048 -f "$SSH_DIR/id_rsa" -N ""
    log "SSH key pair generated"
fi

cat "$SSH_DIR/id_rsa.pub" > "$SSH_DIR/authorized_keys"
chmod 700 "$SSH_DIR"
chmod 600 "$SSH_DIR/id_rsa"
chmod 644 "$SSH_DIR/authorized_keys"
chown -R "$USERNAME:$USERNAME" "$SSH_DIR"
log "SSH keys configured"

# ── STEP 4: FLAGS ─────────────────────────────────────────
section "STEP 4 — Flags"
USER_FLAG=$(openssl rand -hex 16)
ROOT_FLAG=$(openssl rand -hex 16)

# User flag
echo "$USER_FLAG" > "/home/$USERNAME/user.txt"
chown "root:$USERNAME" "/home/$USERNAME/user.txt"
chmod 644 "/home/$USERNAME/user.txt"

# Root flag
echo "$ROOT_FLAG" > /root/root.txt
chown root:root /root/root.txt
chmod 640 /root/root.txt

log "User flag: $USER_FLAG"
log "Root flag: $ROOT_FLAG"

# Verify
USER_LEN=$(cat "/home/$USERNAME/user.txt" | wc -c)
ROOT_LEN=$(cat /root/root.txt | wc -c)
[ "$USER_LEN" -eq 33 ] && log "User flag length OK (32 chars)" || error "User flag length wrong: $USER_LEN"
[ "$ROOT_LEN" -eq 33 ] && log "Root flag length OK (32 chars)" || error "Root flag length wrong: $ROOT_LEN"

# ── STEP 5: SUDO CONFIG ───────────────────────────────────
section "STEP 5 — Sudo Configuration"
# Remove all old HTB sudo entries
sed -i '/htbuser\|aria\|nexus/d' /etc/sudoers 2>/dev/null || true

case "$PRIVESC_TYPE" in
    sudo)
        echo "$USERNAME ALL=(ALL) NOPASSWD: /usr/bin/python3" >> /etc/sudoers
        log "Sudo privesc configured: NOPASSWD python3"
        ;;
    cron|suid|capabilities)
        log "No sudo needed for privesc type: $PRIVESC_TYPE"
        ;;
    *)
        warn "Unknown privesc type: $PRIVESC_TYPE — no sudo configured"
        ;;
esac

# ── STEP 6: INSTALL DEPENDENCIES ─────────────────────────
section "STEP 6 — Dependencies"
apt update -y -q
apt install -y -q python3 python3-pip git openssh-server net-tools curl cron
log "System packages installed"

# ── STEP 7: CLONE AND INSTALL APP ─────────────────────────
section "STEP 7 — Application"
rm -rf "$APP_DIR"
mkdir -p "$APP_DIR"
cd "$APP_DIR"

git clone "$REPO_URL" . 2>&1 | tail -3
log "Repo cloned to $APP_DIR"

if [ -f "requirements.txt" ]; then
    pip3 install -r requirements.txt --break-system-packages -q
    log "Python dependencies installed"
fi

# ── STEP 8: PRIVESC SETUP ─────────────────────────────────
section "STEP 8 — PrivEsc: $PRIVESC_TYPE"
case "$PRIVESC_TYPE" in
    cron)
        # Writable cron script
        BACKUP_SCRIPT="$APP_DIR/backup.sh"
        mkdir -p "$APP_DIR/data"
        cat > "$BACKUP_SCRIPT" << 'CRONEOF'
#!/bin/bash
cp -r /opt/data /tmp/backup 2>/dev/null
CRONEOF
        chmod 777 "$BACKUP_SCRIPT"
        chown "root:$USERNAME" "$BACKUP_SCRIPT"

        # Remove old cron entries and add new
        sed -i "/$MACHINE_LOWER\|backup\.sh/d" /etc/crontab
        echo "* * * * * root $BACKUP_SCRIPT" >> /etc/crontab

        service cron start 2>/dev/null || true
        systemctl enable cron 2>/dev/null || true
        log "Cron privesc configured: $BACKUP_SCRIPT (777)"
        log "Cron entry: * * * * * root $BACKUP_SCRIPT"
        ;;

    suid)
        # SUID binary privesc
        cp /usr/bin/find "$APP_DIR/find_util"
        chmod u+s "$APP_DIR/find_util"
        chown root "$APP_DIR/find_util"
        log "SUID privesc configured: $APP_DIR/find_util"
        warn "PrivEsc command: $APP_DIR/find_util . -exec /bin/sh -p \; -quit"
        ;;

    capabilities)
        # Capabilities privesc
        cp /usr/bin/python3 "$APP_DIR/python3"
        setcap cap_setuid+ep "$APP_DIR/python3"
        log "Capabilities privesc configured: cap_setuid on $APP_DIR/python3"
        warn "PrivEsc command: $APP_DIR/python3 -c 'import os; os.setuid(0); os.system(\"/bin/bash\")'"
        ;;

    sudo)
        log "Sudo privesc already configured in Step 5"
        ;;
esac

# ── STEP 9: SSH CONFIG ────────────────────────────────────
section "STEP 9 — SSH Configuration"
sed -i 's/#PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sed -i 's/#PubkeyAuthentication.*/PubkeyAuthentication yes/' /etc/ssh/sshd_config
sed -i 's/#AuthorizedKeysFile.*/AuthorizedKeysFile .ssh\/authorized_keys/' /etc/ssh/sshd_config

service ssh restart
log "SSH configured and restarted"

# ── STEP 10: SYSTEMD SERVICE ──────────────────────────────
section "STEP 10 — Systemd Service"
SERVICE_FILE="/etc/systemd/system/$MACHINE_LOWER.service"
cat > "$SERVICE_FILE" << SVCEOF
[Unit]
Description=$MACHINE_NAME HTB Machine
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$APP_DIR
ExecStart=/usr/bin/python3 $APP_DIR/$APP_ENTRY
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
SVCEOF

systemctl daemon-reload
systemctl enable "$MACHINE_LOWER"
systemctl start "$MACHINE_LOWER"
sleep 2

# Verify app is running
if systemctl is-active --quiet "$MACHINE_LOWER"; then
    log "App service running: $MACHINE_LOWER.service"
else
    warn "Service may have failed — check: journalctl -u $MACHINE_LOWER"
fi

# Quick API check
sleep 2
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:$APP_PORT/api/status" 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ]; then
    log "API responding on port $APP_PORT ✓"
else
    warn "API not responding yet (HTTP $HTTP_CODE) — may need a moment"
fi

# ── STEP 11: BASH HISTORY CLEANUP ────────────────────────
section "STEP 11 — Cleanup"
ln -sf /dev/null "/home/$USERNAME/.bash_history"
ln -sf /dev/null /root/.bash_history
history -c
log "Bash history cleaned"

# ── FINAL SUMMARY ─────────────────────────────────────────
echo ""
echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}${BOLD}  ✓ $MACHINE_NAME SETUP COMPLETE${NC}"
echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  ${BOLD}Machine:${NC}      $MACHINE_NAME ($DIFFICULTY)"
echo -e "  ${BOLD}Hostname:${NC}     $MACHINE_LOWER"
echo -e "  ${BOLD}User:${NC}         $USERNAME / $USER_PASSWORD"
echo -e "  ${BOLD}App Port:${NC}     $APP_PORT"
echo -e "  ${BOLD}SSH Port:${NC}     22"
echo -e "  ${BOLD}PrivEsc:${NC}      $PRIVESC_TYPE"
echo -e "  ${BOLD}App Dir:${NC}      $APP_DIR"
echo ""
echo -e "  ${YELLOW}${BOLD}FLAGS (save these!):${NC}"
echo -e "  ${BOLD}User Flag:${NC}    $USER_FLAG"
echo -e "  ${BOLD}Root Flag:${NC}    $ROOT_FLAG"
echo ""
echo -e "  ${BOLD}User flag path:${NC} /home/$USERNAME/user.txt"
echo -e "  ${BOLD}Root flag path:${NC} /root/root.txt"
echo ""
echo -e "  ${BOLD}Log file:${NC}     $LOGFILE"
echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}  Next step: Export VM as .ova from VirtualBox${NC}"
echo ""