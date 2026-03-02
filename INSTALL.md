# VertexBrain — VM Installation Guide
**HTB Insane Machine | Vertex Coders LLC**

---

## Prerequisites

- Ubuntu 22.04 Server VM (VirtualBox)
- 4GB RAM minimum (TinyLlama needs ~2GB)
- 30GB disk
- Internet connection during setup

---

## Step 0 — Docker Cleanup

```bash
docker ps -aq | xargs docker stop 2>/dev/null || true
docker ps -aq | xargs docker rm 2>/dev/null || true
docker images -q | xargs docker rmi 2>/dev/null || true
```

## Step 1 — Hostname

```bash
hostnamectl set-hostname vertexbrain
echo "vertexbrain" > /etc/hostname
sed -i "s/$(hostname)/vertexbrain/g" /etc/hosts
```

## Step 2 — Create User

```bash
# Remove old users
userdel -r htbuser 2>/dev/null || true
userdel -r nexus 2>/dev/null || true

# Create vertex user
useradd -m -s /bin/bash vertex
echo "vertex:V3rt3xS3cur3!" | chpasswd
```

## Step 3 — SSH Keys

```bash
SSH_DIR="/home/vertex/.ssh"
mkdir -p $SSH_DIR
ssh-keygen -t rsa -b 2048 -f $SSH_DIR/id_rsa -N ""
cat $SSH_DIR/id_rsa.pub > $SSH_DIR/authorized_keys
chmod 700 $SSH_DIR
chmod 600 $SSH_DIR/id_rsa
chmod 644 $SSH_DIR/authorized_keys
chown -R vertex:vertex $SSH_DIR
```

## Step 4 — SSH Configuration

```bash
sed -i 's/#PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
sed -i 's/#PubkeyAuthentication.*/PubkeyAuthentication yes/' /etc/ssh/sshd_config
sed -i 's/#AuthorizedKeysFile.*/AuthorizedKeysFile .ssh\/authorized_keys/' /etc/ssh/sshd_config
service ssh restart
```

## Step 5 — Flags

```bash
USER_FLAG=$(openssl rand -hex 16)
ROOT_FLAG=$(openssl rand -hex 16)

echo $USER_FLAG > /home/vertex/user.txt
chown vertex:vertex /home/vertex/user.txt
chmod 644 /home/vertex/user.txt

echo $ROOT_FLAG > /root/root.txt
chmod 640 /root/root.txt

echo "User: $USER_FLAG"
echo "Root: $ROOT_FLAG"
```

## Step 6 — Sudo PrivEsc

```bash
# Remove old sudo entries
sed -i '/htbuser\|nexus\|vertex/d' /etc/sudoers

# Add vertex sudo python3 (privesc vector)
echo 'vertex ALL=(ALL) NOPASSWD: /usr/bin/python3' >> /etc/sudoers
```

## Step 7 — Install Dependencies

```bash
apt update -y
apt install -y python3 python3-pip git openssh-server \
    curl wget net-tools build-essential
```

## Step 8 — Install vLLM + TinyLlama

```bash
pip3 install vllm --break-system-packages

# Pre-download TinyLlama model
python3 -c "from transformers import AutoModelForCausalLM; AutoModelForCausalLM.from_pretrained('TinyLlama/TinyLlama-1.1B-Chat-v0.4')"
```

## Step 9 — Clone & Install App

```bash
rm -rf /opt/vertexbrain
mkdir -p /opt/vertexbrain
cd /opt/vertexbrain

git clone https://github.com/Denisijcu/VertexBrain.git .
pip3 install -r requirements.txt --break-system-packages
```

## Step 10 — Systemd Services

```bash
# vLLM service
cat > /etc/systemd/system/vllm.service << 'EOF'
[Unit]
Description=vLLM TinyLlama Server
After=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/bin/python3 -m vllm.entrypoints.openai.api_server \
    --model TinyLlama/TinyLlama-1.1B-Chat-v0.4 \
    --host 127.0.0.1 \
    --port 8000 \
    --max-model-len 2048
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# VertexBrain app service
cat > /etc/systemd/system/vertexbrain.service << 'EOF'
[Unit]
Description=VertexBrain RAG Platform
After=network.target vllm.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/vertexbrain
ExecStart=/usr/bin/uvicorn main:app --host 0.0.0.0 --port 1337
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable vllm vertexbrain
systemctl start vllm
sleep 20  # wait for model to load
systemctl start vertexbrain
```

## Step 11 — Verify

```bash
echo "=== HOSTNAME ===" && hostname
echo "=== APP ===" && curl -s http://127.0.0.1:1337/api/health | python3 -m json.tool
echo "=== vLLM ===" && curl -s http://127.0.0.1:8000/v1/models
echo "=== SSH ===" && service ssh status | grep Active
echo "=== FLAGS ===" && cat /home/vertex/user.txt && cat /root/root.txt
echo "=== SUDO ===" && sudo -l -U vertex
```

## Step 12 — Cleanup

```bash
ln -sf /dev/null /home/vertex/.bash_history
ln -sf /dev/null /root/.bash_history
history -c
```

## Step 13 — Export OVA

```
VirtualBox → File → Export Appliance
→ Name: VertexBrain
→ Format: OVF 1.0
→ VertexBrain.ova
→ Export
```

---

## Attack Chain Reference

```
nmap → 1337 + 22
  → /api/health → fingerprint
    → /docs → all endpoints exposed
      → GitHub source → admin/vertex2025 + SECRET_KEY
        → Login → JWT admin token
          → Upload malicious PDF → RAG Poisoning
            → Query → Prompt Injection → RCE
              → SSH vertex (key from RCE)
                → sudo python3 → root
                  → cat /root/root.txt
```