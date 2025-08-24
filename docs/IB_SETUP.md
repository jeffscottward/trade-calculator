# Interactive Brokers API Setup Guide

## Overview

This system supports two different IB API connections:

1. **Client Portal API** (REST API) - For account info and simple orders
2. **TWS API** (Socket-based) - For robust automated trading

## Current Setup: Client Portal Gateway

### Installation

The Client Portal Gateway is already included in the `clientportal.gw` directory.

### Starting the Gateway

```bash
# Automatic start with all services
./scripts/start-dev.sh

# Or manually start just the gateway
cd clientportal.gw
./bin/run.sh root/conf.yaml
```

The gateway runs on port 5001 (configured to avoid conflicts with port 5000).

### Authentication Requirements

**IMPORTANT**: The Client Portal Gateway requires manual browser-based authentication. This is a limitation of the IB Client Portal API.

#### Steps to Authenticate

1. Start the Client Portal Gateway (runs on port 5001)
2. Open your browser and navigate to: <https://localhost:5001>
3. Accept the self-signed certificate warning
4. Log in with your IB credentials:
   - **Check `.env` file for `IB_BROWSER_USERNAME`**
   - **Check `.env` file for `IB_BROWSER_PASSWORD`** (optional, for convenience)
5. Complete any 2FA if required
6. After successful login, you'll see "Client login succeeds" on the page
7. **Keep the browser tab open** during your trading session

**Note**: The browser login username is different from the API credentials. The API will use the paper trading account (DUM451177) after browser authentication.

### Session Management

- Authentication expires after a period of inactivity
- You may need to re-authenticate periodically
- The session is browser-based, so closing the browser will require re-authentication

## Alternative: TWS/IB Gateway (Recommended for Production)

For fully automated trading without manual authentication, use TWS or IB Gateway:

### Download and Install

1. Download IB Gateway from: <https://www.interactivebrokers.com/en/index.php?f=5041>
2. Install and launch IB Gateway
3. Log in with paper trading credentials

### Configure for API Access

1. In IB Gateway, go to Configure → Settings → API → Settings
2. Enable these options:
   - ✅ Enable ActiveX and Socket Clients
   - ✅ Download open orders on connection
   - ✅ Include market data in snapshot
3. Set Socket port to 7497 (paper trading)
4. Add 127.0.0.1 to trusted IPs
5. Apply and restart IB Gateway

### Connection Ports

- **Paper Trading**: Port 7497
- **Live Trading**: Port 7496
- **Client Portal**: Port 5001

## Testing Your Connection

Run the test script to verify connectivity:

```bash
venv/bin/python automation/test_ib_simple.py
```

Expected output:

- ✅ Client Portal is running (after manual login)
- ✅ TWS/Gateway connected (if using IB Gateway)

## Trade Execution Flow

### Using Client Portal API

1. Ensure Client Portal Gateway is running
2. Complete browser authentication
3. Keep browser tab open
4. Execute trades via `ib_api_client.py`

### Using TWS API (Recommended)

1. Ensure IB Gateway is running and configured
2. No manual authentication needed after initial setup
3. Execute trades via `trade_executor.py`

## Troubleshooting

### Client Portal Issues

**Error: 401 Unauthorized**

- Solution: Complete browser authentication at <https://localhost:5001>

**Error: Connection refused on port 5001**

- Solution: Start Client Portal Gateway with `./scripts/start-dev.sh`

**Error: Certificate warning**

- Solution: This is expected. Accept the self-signed certificate.

### TWS/IB Gateway Issues

**Error 502: Couldn't connect to TWS**

- Solution: Ensure IB Gateway is running on port 7497
- Check API settings are enabled

**Error: No security definition found**

- Solution: Ensure market data subscriptions are active

## Best Practices

1. **For Development**: Use Client Portal with manual authentication
2. **For Production**: Use IB Gateway for unattended operation
3. **Keep Sessions Active**: Periodic API calls prevent timeout
4. **Error Handling**: Implement reconnection logic for production
5. **Paper Trading First**: Always test with paper account before live

## Security Notes

- Never commit credentials to version control
- Use environment variables for sensitive data
- The Client Portal uses self-signed certificates (this is normal)
- Keep your paper and live accounts separate

## API Limitations

### Client Portal API

- Requires manual browser authentication
- Session expires after inactivity
- Limited to simpler order types
- Good for account info queries

### TWS API

- Full automation capability
- Supports all order types
- Better for high-frequency operations
- Requires IB Gateway installation

## Support

- IB API Documentation: <https://www.interactivebrokers.com/api/doc.html>
- Discord Community: <https://discord.gg/krdByJHuHc>
- IB Support: <api@ibkr.com>
