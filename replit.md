# Discord IP Logger & UNITED HUB Verification

## Overview

This is a Flask-based web application that serves two purposes:
1. **IP Logger**: Captures detailed user information (IP, location, device info) and sends to Discord webhook
2. **UNITED HUB**: Roblox script verification system with discrete interface that logs access attempts

The application provides multiple interfaces: detailed IP logging system and a clean verification system for the UNITED HUB Roblox script.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Architecture
- **Framework**: Flask (Python web framework)
- **Deployment**: Configured for reverse proxy environments using ProxyFix middleware
- **Session Management**: Uses Flask's built-in session handling with configurable secret key
- **Logging**: Python's built-in logging module for debugging and monitoring

### Frontend Architecture
- **Template Engine**: Jinja2 (Flask's default)
- **CSS Framework**: Bootstrap 5 with dark theme from Replit CDN
- **Icons**: Font Awesome 6.0.0
- **Responsive Design**: Mobile-first approach using Bootstrap's grid system

## Key Components

### Core Application (app.py)
- **Flask App**: Main application instance with proxy configuration and PostgreSQL database
- **IP Detection**: Multi-layered IP address detection considering various proxy headers
- **Geolocation**: Integration with ipapi.co for real location detection (city/state/country)
- **Device Detection**: User-Agent parsing for OS version, browser, and device type identification
- **Discord Integration**: Multiple webhook endpoints for comprehensive monitoring
- **UNITED HUB**: Verification system for Roblox script access with discrete interface
- **Key Management**: PostgreSQL-based system with automatic 24-hour expiration
- **Private API**: Secure endpoints for Discord bot integration with authentication
- **Error Handling**: Comprehensive error handling for external API calls and database operations

### Entry Point (main.py)
- Simple application runner for development environment
- Configured for host binding and debug mode

### Templates
#### IP Logger System:
- **index.html**: Landing page with usage instructions and form interface
- **success.html**: Detailed confirmation page showing all captured data (IP, location, device info)
- **error.html**: Error handling page with troubleshooting guidance

#### UNITED HUB System:
- **hub.html**: Clean verification interface for Roblox script access
- **verified.html**: Success page with simple "Verificado com sucesso" message
- **denied.html**: Access denied page for invalid keys

## Data Flow

### IP Logger System:
1. **User Access**: User visits via URL parameter (/track?user=name) or form submission
2. **Data Collection**: Application captures IP, geolocation, OS version, browser, device type
3. **Discord Notification**: Detailed information sent to Discord with emojis and formatting
4. **User Feedback**: Detailed success page showing all captured information

### UNITED HUB System:
1. **Page Access Tracking**: Every visit to the site is logged with user details
2. **Key Verification**: User enters verification key for access
3. **Dual Logging**: All attempts sent to both main webhook and DM notification webhook
4. **Discrete Response**: Simple success/failure message without revealing captured data
5. **Background Monitoring**: Complete user details sent to Discord for monitoring
6. **Private Key Generation**: API endpoint for Discord bots to create user-specific keys

### Discord Bot Integration:
1. **Command Processing**: Bot responds to /gerarsenha command in Discord
2. **Private Key Creation**: Uses secure API to generate unique keys per user
3. **DM Delivery**: Keys sent privately to requesting user
4. **Admin Notifications**: All site activity forwarded to admin DM webhook

## External Dependencies

### Python Packages
- **Flask**: Web framework for application structure
- **Requests**: HTTP library for Discord webhook communication and geolocation API calls
- **Werkzeug**: WSGI utilities including ProxyFix middleware
- **User-Agents**: Library for parsing User-Agent strings to detect OS and device info

### External Services
- **Discord Webhooks**: Multiple webhooks for different purposes
  - Main verification webhook: Site access and key verification attempts
  - Key generation webhook: New key notifications  
  - DM notification webhook: Private notifications for admins
- **ipapi.co**: Free geolocation service for IP address location lookup
- **CDN Resources**: Bootstrap CSS and Font Awesome icons from external CDNs

### Environment Variables
- `DISCORD_WEBHOOK_URL`: Main Discord webhook endpoint (required for production)
- `SESSION_SECRET`: Flask session encryption key (optional, defaults to dev key)
- `API_SECRET_KEY`: Secret key for private API authentication (for Discord bot integration)

## Deployment Strategy

### Environment Configuration
- Designed for containerized or reverse proxy deployment
- ProxyFix middleware handles X-Forwarded headers correctly
- Configurable via environment variables for different environments

### Security Considerations
- IP address detection handles multiple proxy scenarios
- Session secret should be set in production environments
- Webhook URL should be secured and not exposed in code

### Scalability
- Stateless design allows for horizontal scaling
- External webhook communication with proper timeout handling
- Error resilience with fallback mechanisms

### Development vs Production
- Debug mode enabled in main.py for development
- Environment-based configuration for webhook URLs and secrets
- Comprehensive logging for troubleshooting and monitoring