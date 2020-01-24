#!/bin/bash

# function is_ip {
#     UPKI_IP="$1"
#     # Check if the format looks right_
#     echo "$UPKI_IP" | egrep -qE '[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}' || return 1
#     #check that each octect is less than or equal to 255:
#     echo $UPKI_IP | awk -F'.' '$1 <=255 && $2 <= 255 && $3 <=255 && $4 <= 255 {print "Y" } ' | grep -q Y || return 1
#     return 0
# }

# function is_port {
#     UPKI_PORT="$1"
#     local -i port_num=$(to_int "${UPKI_PORT}" 2>/dev/null)
#     if (( $port_num < 1 || $port_num > 65535 )) ; then
#         return 1
#     fi
#     return 0
# }

# # Request CA listening ip from user if needed
# if [[ -z "$UPKI_IP" ]]; then
#     read -p "Enter CA listening IP [127.0.0.1]: " UPKI_IP
#     UPKI_IP=${UPKI_IP:-127.0.0.1}
#     while ! is_ip "$UPKI_IP"
#     do
#         read -p "Not an IP. Re-enter: " UPKI_IP
#     done
# fi

# # Request CA listening port from user if needed
# if [[ -z "$UPKI_PORT" ]]; then
#     read -p "Enter CA listening port [5000]: " UPKI_PORT
#     UPKI_PORT=${UPKI_PORT:-5000}
#     while ! is_port "$UPKI_PORT"
#     do
#         read -p "Not a valid PORT. Re-enter: " UPKI_PORT
#     done
# fi

function is_url {
    regex='(https?)://[-A-Za-z0-9\+&@#/%?=~_|!:,.;]*[-A-Za-z0-9\+&@#/%=~_|]'
    if [[ $1 =~ $regex ]]; then
        return 0
    fi
    return 1
}

function is_seed {
    regex='^([0-9a-fA-F]{32,64})$'
    if [[ $1 =~ $regex ]]; then
        return 0
    fi
    return 1
}

echo -e "\t\t..:: µPki Registration Authority Installer ::.."
echo ""

# If user is not root, try sudo
if [[ $EUID -ne 0 ]]; then
    sudo -p "Enter your password: " whoami 1>/dev/null 2>/dev/null
    if [ ! $? = 0 ]; then 
        echo "You entered an invalid password or you are not an admin/sudoer user. Script aborted."
        exit 1
    fi
fi

# Setup user vars
USERNAME=${USER}
GROUPNAME=$(id -gn $USER)
INSTALL=${PWD}

# Setup UPKI default vars
UPKI_DIR="${HOME}/.upki"
UPKI_IP='127.0.0.1'
UPKI_PORT=5000
UPKI_URL=''
UPKI_SEED=''
UPKI_DOMAIN=''

usage="$(basename "$0") [-h] [-u https://certificates.domain.com] [-d ${UPKI_DIR}] [-i ${UPKI_IP}] [-p ${UPKI_PORT}] -- Install script for uPKI Registration Authority

where:
    -h  show this help text
    -u  set your listening domain that the world will use (https://certificates.domain.com)
    -s  set the register SEED value
    -d  set the install directory for logs and storage
    -i  set the CA listening IP (default: 127.0.0.1)
    -p  set the CA listening port (default: 5000)
"

while getopts ':husdip:' option; do
  case "$option" in
    h) echo "$usage"
       exit
       ;;
    u) UPKI_URL=$OPTARG
       ;;
    s) UPKI_SEED=$OPTARG
       ;;
    d) UPKI_DIR=$OPTARG
       ;;
    i) UPKI_IP=$OPTARG
       ;;
    p) UPKI_PORT=$OPTARG
       ;;
    :) printf "missing argument for -%s\n" "$OPTARG" >&2
       echo "$usage" >&2
       exit 1
       ;;
   \?) printf "illegal option: -%s\n" "$OPTARG" >&2
       echo "$usage" >&2
       exit 1
       ;;
  esac
done
shift $((OPTIND - 1))

# Request CA listening ip from user if needed
if [[ -z "$UPKI_URL" ]]; then
    read -p "Enter public url: " UPKI_URL
    while ! is_url "$UPKI_URL"
    do
        read -p "Not a valid URL. Re-enter: " UPKI_URL
    done
fi

# Extract domain from url
UPKI_DOMAIN=$(echo "${UPKI_URL}" | cut -d'/' -f3)

# Update system & install required apps
echo "[+] Update system"
sudo apt -y update && sudo apt -y upgrade
echo "[+] Install required apps"
sudo apt -y install build-essential python3-dev python3-pip git nginx

# Install required libs
echo "[+] Install required libs"
pip3 install -r requirements.txt

# Request CA register SEED value from user if needed
if [[ -z "$UPKI_SEED" ]]; then
    read -p "Enter register SEED value (value delivered by upki during installation): " UPKI_SEED
    while ! is_seed "$UPKI_SEED"
    do
        read -p "Not a valid SEED. Re-enter: " UPKI_SEED
    done
fi

# Launch uPKI registration
echo "[+] Launching registration against tcp://${UPKI_IP}:${UPKI_PORT} with SEED: ${UPKI_SEED}"
./ra_server.py --ip ${UPKI_IP} --port ${UPKI_PORT} register --seed ${UPKI_SEED}

echo "[+] Create services & timers"
# Create ra service
tee /tmp/upki-ra.service > /dev/null <<EOT
[Unit]
Description=µPki Registration Authority service
ConditionACPower=true
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${USERNAME}
Group=${GROUPNAME}
Restart=on-failure
WorkingDirectory=${INSTALL}
ExecStart=/usr/bin/python3 ./ra_server.py --dir ${UPKI_DIR} --ip ${UPKI_IP} --port ${UPKI_PORT} listen

[Install]
WantedBy=multi-user.target
EOT

# Create CRL generation service
tee /tmp/upki-ra-crl.service > /dev/null <<EOT
[Unit]
Description=µPki CRL generation service
ConditionACPower=true
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${USERNAME}
Group=${GROUPNAME}
Restart=on-failure
WorkingDirectory=${INSTALL}
ExecStart=/usr/bin/python3 ./ra_server.py --dir ${UPKI_DIR} --ip ${UPKI_IP} --port ${UPKI_PORT} crl
ExecStartPost=/usr/sbin/service nginx restart
# ExecStartPost=/usr/sbin/service apache2 restart

[Install]
WantedBy=upki-ra-crl.timer
EOT

# Create CRL timer (every days @ 2:AM)
tee /tmp/upki-ra-crl.timer > /dev/null <<EOT
[Unit]
Description=µPki CRL generation service timer

[Timer]
OnBootSec=1min
OnCalendar= *-*-* 02:00:00
RandomizedDelaySec=1hour
Unit=upki-ra.service
Persistent=true

[Install]
WantedBy=timers.target
EOT

# Move files if possible
sudo mv /tmp/upki-ra.service /etc/systemd/system/
sudo mv /tmp/upki-ra-crl.service /etc/systemd/system/
sudo mv /tmp/upki-ra-crl.timer /etc/systemd/system/

# Setup website
if [[ ! -d "/var/www/upki" ]]; then
    echo "[+] Create website"
    sudo mkdir -p /var/www/upki
    sudo chown -R $USERNAME.$GROUPNAME /var/www/upki
    git clone --quiet https://github.com/proh4cktive/upki-web.git /var/www/upki
fi

# Setup Nginx config name bucket
if [[ -f "/etc/nginx/conf.d/upki.conf" ]]; then
    sudo cat "server_names_hash_bucket_size 64;" > "/etc/nginx/conf.d/upki.conf"
fi

# Create pre-configured VHOST for NGINX
if [[ -d "/etc/nginx/sites-available" ]]; then
    tee /tmp/nginx_upki.conf > /dev/null <<EOT
server {
    listen 80;
    server_name ${UPKI_DOMAIN};
    return 301 https://\$host\$request_uri;
}

server {
    listen 443 ssl;
    server_name ${UPKI_DOMAIN};

    charset utf-8;
    index index.html;
    
    # Redirect non-https traffic to https
    if (\$scheme != "https") {
        return 301 https://\$host\$request_uri;
    }

    ssl_protocols TLSv1.1 TLSv1.2;
    ssl_prefer_server_ciphers on;
    ssl_certificate ${UPKI_DIR}/certificates.crt;
    ssl_certificate_key ${UPKI_DIR}/certificates.key;

    ssl_client_certificate ${UPKI_DIR}/ca.crt;
    ssl_crl ${UPKI_DIR}/crl.pem;
    ssl_verify_client optional;

    ssl_ciphers "ECDHE-ECDSA-AES128-GCM-SHA256 ECDHE-ECDSA-AES256-GCM-SHA384 ECDHE-ECDSA-AES128-SHA ECDHE-ECDSA-AES256-SHA ECDHE-ECDSA-AES128-SHA256 ECDHE-ECDSA-AES256-SHA384 ECDHE-RSA-AES128-GCM-SHA256 ECDHE-RSA-AES256-GCM-SHA384 ECDHE-RSA-AES128-SHA ECDHE-RSA-AES128-SHA256 ECDHE-RSA-AES256-SHA384 DHE-RSA-AES128-GCM-SHA256 DHE-RSA-AES256-GCM-SHA384 DHE-RSA-AES128-SHA DHE-RSA-AES256-SHA DHE-RSA-AES128-SHA256 DHE-RSA-AES256-SHA256 EDH-RSA-DES-CBC3-SHA";

    access_log /var/log/nginx/upki.access.log;
    error_log /var/log/nginx/upki.error.log;

    location = /favicon.ico { access_log off; log_not_found off; }
    location = /robots.txt  { access_log off; log_not_found off; }
 
    location ~ /\.ht {
        deny all;
    }

    # Public unprotected requests
    location ~ ^/(ocsp|magic|certs|certify)/? {
        proxy_redirect off;
        proxy_set_header Host \$host;
        proxy_set_header Access-Control-Allow-Origin: \$http_origin;
        proxy_set_header Access-Control-Allow-Credentials: true;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_pass      http://127.0.0.1:8000;
    }

    # Client or Admin restricted requests
    location ~ ^/(clients/renew|private)/? {
        if (\$ssl_client_verify != SUCCESS) {
           return 404;
        }   
        proxy_redirect off;
        proxy_set_header Host \$host;
        proxy_set_header Access-Control-Allow-Origin: \$http_origin;
        proxy_set_header Access-Control-Allow-Credentials: true;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header SSL-Client-Verify \$ssl_client_verify;
        proxy_set_header SSL-Client-DN \$ssl_client_s_dn;
        proxy_pass      http://127.0.0.1:8000;
    }

    location @rewrites {
        rewrite ^(.+)$ /index.html last;
    }

    # RA web interface (administration)
    location / {
        if (\$ssl_client_verify != SUCCESS) {
            return 404;
        }
        try_files $uri $uri/ @rewrites;
        add_header Host \$host;
        add_header Access-Control-Allow-Origin: \$http_origin;
        add_header Access-Control-Allow-Credentials: true;
        add_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        add_header Upgrade \$http_upgrade;
        add_header Connection "upgrade";
        add_header SSL-Client-Verify \$ssl_client_verify;
        add_header SSL-Client-DN \$ssl_client_s_dn;
        root /var/www/upki/dist;
    }
}
EOT
    # Adapt domain in website
    sed -i "s/certificates.kitchen.io/${UPKI_DOMAIN}/g" /var/www/upki/dist/js/*
    # Copy file
    sudo mv /tmp/nginx_upki.conf /etc/nginx/sites-available/upki.conf
    # Enable vhost
    echo "[+] Enable vhost in Nginx"
    sudo ln -s /etc/nginx/sites-available/upki.conf /etc/nginx/sites-enabled/upki
    echo "[+] Restart Nginx"
    # Restart Nginx
    sudo service nginx restart
fi

# Reload services
sudo systemctl daemon-reload

echo "Do you wish to activate uPKI-RA service on boot?"
select yn in "Yes" "No"; do
    case $yn in
        Yes )
            # Start uPKI-RA service & timer
            echo "[+] Activate services & timers"
            sudo systemctl enable upki-ra.service
            sudo systemctl enable upki-ra-crl.timer
            sudo service upki-ra start
            break;;
        No ) exit;;
    esac
done

# Force first CRL generation
# echo "[+] Generate first CRL"
# ${INSTALL}/ra_server.py --dir ${UPKI_DIR} --ip ${UPKI_IP} --port ${UPKI_PORT} crl

echo "[+] All done"
echo ""
