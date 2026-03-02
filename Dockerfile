FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# ── Base packages ────────────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y \
    python3 python3-pip git openssh-server \
    curl wget net-tools sudo cron vim \
    && rm -rf /var/lib/apt/lists/*

# ── Create user: vertex ───────────────────────────────────────────────────────
RUN useradd -m -s /bin/bash vertex && \
    echo 'vertex:V3rt3xS3cur3!' | chpasswd

# ── SSH keys for vertex ───────────────────────────────────────────────────────
RUN mkdir -p /home/vertex/.ssh && \
    ssh-keygen -t rsa -b 2048 -f /home/vertex/.ssh/id_rsa -N "" && \
    cat /home/vertex/.ssh/id_rsa.pub > /home/vertex/.ssh/authorized_keys && \
    chmod 700 /home/vertex/.ssh && \
    chmod 600 /home/vertex/.ssh/id_rsa && \
    chmod 644 /home/vertex/.ssh/authorized_keys && \
    chown -R vertex:vertex /home/vertex/.ssh

# ── SSH configuration ─────────────────────────────────────────────────────────
RUN sed -i 's/#PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config && \
    sed -i 's/#PubkeyAuthentication.*/PubkeyAuthentication yes/' /etc/ssh/sshd_config && \
    sed -i 's/#AuthorizedKeysFile.*/AuthorizedKeysFile .ssh\/authorized_keys/' /etc/ssh/sshd_config

# ── App installation ──────────────────────────────────────────────────────────
WORKDIR /opt/vertexbrain
COPY . .
RUN pip3 install --break-system-packages -r requirements.txt

# ── Sudo privesc: vertex can run python3 as root ──────────────────────────────
RUN echo 'vertex ALL=(ALL) NOPASSWD: /usr/bin/python3' >> /etc/sudoers

# ── Flags ─────────────────────────────────────────────────────────────────────
RUN echo "HTB_USER_FLAG_PLACEHOLDER" > /home/vertex/user.txt && \
    chown vertex:vertex /home/vertex/user.txt && \
    chmod 644 /home/vertex/user.txt

RUN echo "HTB_ROOT_FLAG_PLACEHOLDER" > /root/root.txt && \
    chmod 640 /root/root.txt

# ── Clean bash history ────────────────────────────────────────────────────────
RUN ln -sf /dev/null /home/vertex/.bash_history && \
    ln -sf /dev/null /root/.bash_history

# ── Startup script ────────────────────────────────────────────────────────────
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 22 1337 8000

ENTRYPOINT ["/docker-entrypoint.sh"]