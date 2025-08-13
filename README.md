# Selent MCP

A powerful Model Context Protocol (MCP) server that provides dynamic access to the entire Meraki Dashboard API. Instead of creating hundreds of individual tools, Selent MCP uses intelligent discovery to find and execute any Meraki API endpoint on demand.

## 🚀 Features

### **Dynamic API Discovery**

- **Universal Access**: Query any of 400+ Meraki API endpoints without pre-defined tools
- **Single-Call Optimization**: Common queries (organizations, device status, etc.) found instantly
- **Intelligent Search**: Natural language queries to find relevant endpoints
- **Parameter Discovery**: Automatic detection of required and optional parameters
- **Smart Validation**: Generic parameter validation with helpful error messages

### **Backup & Restore Operations** 🔄

- **Organization Backup**: Create complete backups of your Meraki organization
- **Component Restore**: Restore individual devices or networks from backups
- **Status Monitoring**: Real-time progress tracking for backup and restore operations
- **Error Handling**: Comprehensive error reporting and recovery guidance

> **Note**: Backup and restore functionality requires a **Selent API key**. Contact [Selent](https://selent.ai) to obtain access.

## 🐳 Quick Start with Docker

### 1. Prerequisites

- Docker installed and running
- Meraki Dashboard API key ([Get one here](https://documentation.meraki.com/General_Administration/Other_Topics/Cisco_Meraki_Dashboard_API))
- Selent API key (optional, required for backup/restore features - contact [Selent](https://selent.ai))

### 2. Deploy the Server

**Option A: Use Public Docker Image (Recommended)**

```bash
# Set your API keys
export MERAKI_API_KEY="your_meraki_api_key_here"
export SELENT_API_KEY="your_selent_api_key_here"  # Optional, for backup/restore

# Run directly from Docker Hub
docker run \
  -e MERAKI_API_KEY=$MERAKI_API_KEY \
  -e SELENT_API_KEY=$SELENT_API_KEY \
  -i --rm selentai/selent-mcp:latest
```

**Option B: Build from Source**

```bash
# Clone the repository
git clone <repository-url>
cd selent-mcp

# Set your API keys
export MERAKI_API_KEY="your_meraki_api_key_here"
export SELENT_API_KEY="your_selent_api_key_here"  # Optional, for backup/restore

# Start the server
docker-compose up -d
```

### 3. Configure Claude Desktop

Update your Claude Desktop configuration file:

**Location**: `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS)

```json
{
  "mcpServers": {
    "Selent MCP": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e",
        "MERAKI_API_KEY=your_meraki_api_key_here",
        "-e",
        "SELENT_API_KEY=your_selent_api_key_here",
        "selentai/selent-mcp:latest"
      ]
    }
  }
}
```

### 4. Restart Claude Desktop

Restart Claude Desktop to load the new MCP server.

## 📖 Usage Examples

### **API Operations**

```
# Get device information
"Get device Q4AB-WMAB-TAZU configuration for port number 4"

# List organizations
"Show me all my Meraki organizations"

# Get network clients
"List all clients in network N_12345"

# Firewall rules
"Get MX firewall rules for device Q2KN-Q6GH-CREQ"
```

## 🛠 Development & Management

### **Container Management**

```bash
# Check status
docker ps --filter name=selent-mcp-server

# View logs
docker logs -f selent-mcp-server

# Restart
docker-compose restart

# Stop
docker-compose down

# Rebuild and restart
docker-compose up -d --build
```

## 🔧 Available Tools

### **API Tools**

- `search_meraki_api_endpoints` - Find API endpoints using natural language
- `execute_meraki_api_endpoint` - Execute any Meraki API call
- `get_meraki_endpoint_parameters` - Get parameter requirements for endpoints

## 💡 Key Benefits

✅ **No Manual Tool Creation**: Access 400+ endpoints without writing individual tools  
✅ **Single-Call Efficiency**: Common queries resolved instantly without multiple searches  
✅ **Intelligent Discovery**: Natural language queries find the right endpoints  
✅ **Always Up-to-Date**: Uses live Meraki API, automatically includes new endpoints  
✅ **Production Ready**: Docker deployment for consistency across environments  
✅ **Multi-User Support**: Scale across teams with individual API keys  
✅ **Performance Optimized**: Caching, error handling, and smart parameter validation

## 🔐 Security & Environment

### **Environment Variables**

| Variable              | Required | Description                                                   |
| --------------------- | -------- | ------------------------------------------------------------- |
| `MERAKI_API_KEY`      | Yes      | Your Meraki Dashboard API key                                 |
| `SELENT_API_KEY`      | Optional | Your Selent API key (required for backup/restore)             |
| `SELENT_API_BASE_URL` | Optional | Selent API base URL (defaults to `https://backend.selent.ai`) |

### **Security Best Practices**

- Never commit API keys to version control
- Use environment variables or secure secret management
- Scan Docker images for vulnerabilities in production
- Set appropriate resource limits for containers
- Use secure networks in production deployments

---
