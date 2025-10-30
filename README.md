# Selent MCP

A powerful Model Context Protocol (MCP) server that provides dynamic access to the entire Meraki Dashboard API plus advanced compliance and security auditing capabilities. Instead of creating hundreds of individual tools, Selent MCP uses intelligent discovery to find and execute any Meraki API endpoint on demand.

## 🚀 Features

### **Dynamic API Discovery**

- **Universal Access**: Query any of 400+ Meraki API endpoints without pre-defined tools
- **Single-Call Optimization**: Common queries (organizations, device status, etc.) found instantly
- **Intelligent Search**: Natural language queries to find relevant endpoints
- **Parameter Discovery**: Automatic detection of required and optional parameters
- **Smart Validation**: Generic parameter validation with helpful error messages

### **Compliance & Security Auditing** 🛡️

- **Multi-Framework Support**: PCI DSS, HIPAA, SOC2, ISO 27001, NIST Cybersecurity Framework
- **Automated Compliance Scanning**: Comprehensive security assessments across your entire Meraki organization
- **Critical Finding Detection**: Identifies security gaps and compliance violations
- **Actionable Recommendations**: Specific remediation steps for each finding
- **Detailed Reporting**: Executive summaries and technical details for compliance documentation

### **Backup & Restore Operations** 🔄

- **Organization Backup**: Create complete backups of your Meraki organization
- **Component Restore**: Restore individual devices or networks from backups
- **Status Monitoring**: Real-time progress tracking for backup and restore operations
- **Error Handling**: Comprehensive error reporting and recovery guidance

### **Advanced Network Analysis** 📊

- **Network Topology Analysis**: Comprehensive device relationships and connections
- **Device Health Monitoring**: Performance metrics and diagnostics
- **Security Auditing**: Network-wide security assessments
- **Performance Analytics**: Bottleneck identification and optimization recommendations
- **Configuration Drift Detection**: Identify inconsistencies across networks

> **Note**: Advanced features (backup/restore, compliance auditing) require a **Selent API key**. Contact [Selent](https://selent.ai) to obtain access.

## 🐳 Quick Start with Docker

### 1. Prerequisites

- Docker installed and running
- Meraki Dashboard API key ([Get one here](https://documentation.meraki.com/General_Administration/Other_Topics/Cisco_Meraki_Dashboard_API))
- Selent API key (optional, required for advanced features - contact [Selent](https://selent.ai))

### 2. Deploy the Server

**Option A: Use Public Docker Image (Recommended)**

```bash
# Set your API keys
export MERAKI_API_KEY="your_meraki_api_key_here"
export SELENT_API_KEY="your_selent_api_key_here"  # Optional, for advanced features

# Run directly from Docker Hub (always pulls latest)
docker run \
  --pull=always \
  -e MERAKI_API_KEY=$MERAKI_API_KEY \
  -e SELENT_API_KEY=$SELENT_API_KEY \
  -i --rm selentai/selent-mcp:latest
```

**Option B: Build from Source**

```bash
# Clone the repository
git clone <repository-url>
cd selent-mcp

# Build the Docker image
docker build -t selent-mcp:latest .

docker-compose up -d
```

**Testing the Build**:

```bash
docker run -i --rm \
  -e MERAKI_API_KEY=test_key \
  -e SELENT_API_KEY=test_key \
  selent-mcp:latest
```

### 3. Configure Claude Desktop

Update your Claude Desktop configuration file:

**Location**: `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS)

#### Single Meraki API Key (Production)

```json
{
  "mcpServers": {
    "Selent MCP": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "--pull=always",
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

#### Multiple Meraki API Keys (Multi-Organization Support)

Manage multiple Meraki organizations by providing multiple API keys with labels:

```json
{
  "mcpServers": {
    "Selent MCP": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "--pull=always",
        "-e",
        "MERAKI_API_KEY=org1:api_key_1,org2:api_key_2,org3:api_key_3",
        "-e",
        "SELENT_API_KEY=your_selent_api_key_here",
        "selentai/selent-mcp:latest"
      ]
    }
  }
}
```

**Multi-Key Format**: `label1:api_key_1,label2:api_key_2,...`

With multiple keys configured, you can:

- List all available API keys and their labels
- Switch between different organizations
- Execute API calls against specific organizations


### 4. Restart Claude Desktop

Restart Claude Desktop to load the new MCP server.

### 5. Test Your Configuration

Once Claude Desktop restarts, test your setup:

```
# Test basic API access
"What Meraki organizations do I have access to?"

# Test compliance tools (requires Selent API key)
"What compliance types are available?"

# Test a compliance scan (requires Selent API key)
"Run a PCI compliance test"

# Test licensing features (requires Selent API key)
"Get licensing expirations for my organization"
```

The `--pull=always` flag ensures you automatically get the latest features and security updates without manual intervention.

## 📖 Usage Examples

### **Multi-Key Management**

When multiple Meraki API keys are configured, you can manage them:

```
# List all configured API keys
"List all my Meraki API keys"
"Show me which API keys are configured"

# Switch between organizations
"Switch to organization org1"
"Use the org2 API key"

# Get current active key
"Which API key am I currently using?"
"Show me the current organization"
```

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

# Search for API endpoints
"Find API endpoints related to switch ports"
"How do I get SSID configuration?"
```

### **Compliance Testing**

```
# Get available compliance frameworks
"What compliance types are available?"

# Run PCI DSS compliance test
"Run PCI compliance test on my organization"

# Test SOC2 compliance
"Perform SOC2 compliance audit"

# NIST Cybersecurity Framework assessment
"Run NIST compliance check"
```

### **Backup & Restore**

```
# Create organization backup
"Create a backup of my entire Meraki organization"

# Check backup status
"What's the status of backup abc123?"

# Restore a device
"Restore device Q2XX-XXXX-XXXX from backup abc123"

# Restore a network
"Restore network L_123456789 from backup abc123"
```

### **Advanced Analytics**

```
# Network topology analysis
"Analyze the topology of network N_12345"

# Device health check
"Check the health of device Q2XX-XXXX-XXXX"

# Security audit
"Perform security audit on network N_12345"

# Performance analysis
"Analyze performance of network N_12345"
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

### **Core API Tools**

- `search_meraki_api_endpoints` - Find API endpoints using natural language
- `execute_meraki_api_endpoint` - Execute any Meraki API call
- `get_meraki_endpoint_parameters` - Get parameter requirements for endpoints

### **Multi-Key Management Tools** (available when multiple API keys configured)

- `list_api_keys` - List all configured Meraki API keys
- `get_current_api_key` - Get the currently active API key
- `switch_api_key` - Switch to a different API key by label

### **Selent Advanced Tools** (requires Selent API key)

- `selent_get_licensing_expirations` - Get licensing expiration information
- `selent_get_organization_licensing_summary` - Get organization licensing summary
- `selent_run_compliance_test` - Run compliance tests (PCI, HIPAA, SOC2, ISO 27001, NIST)
- `selent_create_backup` - Create organization backups
- `selent_restore_from_backup` - Restore from backups


## 🔐 Security & Environment

### **Environment Variables**

| Variable              | Required | Description                                                         | Examples                                                                                       |
| --------------------- | -------- | ------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| `MERAKI_API_KEY`      | Yes      | Your Meraki Dashboard API key(s). Supports single or multiple keys. | Single: `your_api_key`<br>Multi: `org1:key1,org2:key2`                                         |
| `SELENT_API_KEY`      | Optional | Your Selent API key (required for advanced features)                | `your_selent_api_key`                                                                          |
| `SELENT_API_BASE_URL` | Optional | Selent API base URL. Defaults to production.                        | Production: `https://backend.selent.ai` 

**Multi-Key Format**: When using multiple Meraki API keys, format them as: `label1:api_key_1,label2:api_key_2,...`

- Labels help identify which organization each key belongs to
- Switch between keys using the key management tools
- All keys remain available throughout the session

### **Security Best Practices**

- Never commit API keys to version control
- Use environment variables or secure secret management
- Scan Docker images for vulnerabilities in production
- Set appropriate resource limits for containers
- Use secure networks in production deployments

---
