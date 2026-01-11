#!/usr/bin/env python3
"""
MCP Server Generator

Helps users create custom MCP servers for any API they want to connect to.
Generates boilerplate code and guides through the setup process.
"""

import logging
import json
import os
from typing import Dict, Any, Optional, List
from pathlib import Path


class MCPGenerator:
    """Generates custom MCP server boilerplate."""

    def __init__(self):
        """Initialize the MCP generator."""
        self.logger = logging.getLogger(__name__)

    def get_custom_mcp_wizard_welcome(self) -> str:
        """Get welcome message for custom MCP server wizard.

        Returns:
            Welcome message with Ralph's personality
        """
        return """*Custom MCP Server Wizard* 🧙‍♂️

Me Ralph! Me help you build your very own MCP server!

**What is this?**
Want Claude to connect to an API that doesn't have an MCP server yet?
Me help you build one from scratch! Is like making a custom app for Claude!

**What you'll need:**
→ Name of the API you want to connect to
→ API documentation URL
→ API key or auth details (if needed)
→ What you want Claude to be able to do with it

**Me walk you through:**
1️⃣ Tell me about your API
2️⃣ Me generate starter code for you
3️⃣ Me guide you through config
4️⃣ Test it works!
5️⃣ Use with Claude Code!

Ready to build? Let's gooo! 🚀"""

    def get_api_info_prompt(self) -> str:
        """Get prompt asking for API information.

        Returns:
            Message asking for API details
        """
        return """*Tell Ralph about your API!* 🔌

**What API do you want to connect to?**

Please tell me:
1. **API Name** (e.g., "Stripe", "Twilio", "Your Company API")
2. **What it does** (in your own words)
3. **Documentation URL** (if you have it)

Example:
"Me want to connect to Stripe! Is for payments. Docs at https://stripe.com/docs/api"

Just type your answer naturally! Me Ralph will understand! 🧠"""

    def get_auth_type_prompt(self) -> str:
        """Get prompt asking about authentication type.

        Returns:
            Message asking about auth method
        """
        return """*How does your API handle auth?* 🔐

Pick the type that matches your API:

**1. API Key** 🔑
→ You have a simple API key/token
→ Example: `Authorization: Bearer sk_live_abc123`

**2. OAuth 2.0** 🔄
→ You need to login and get tokens
→ Example: GitHub, Google, Slack

**3. Basic Auth** 👤
→ Username and password
→ Example: Some internal APIs

**4. No Auth** ✅
→ Public API, no authentication needed

**5. Other/Custom** ⚙️
→ Something more complex

Just type the number or name! (e.g., "API Key" or "1")"""

    def get_capabilities_prompt(self) -> str:
        """Get prompt asking what capabilities user wants.

        Returns:
            Message asking about desired MCP tools
        """
        return """*What should Claude be able to do?* 🛠️

Tell me what actions you want Claude to perform with this API!

**Examples:**
→ "Send messages"
→ "Get user data"
→ "Create payments"
→ "Search records"
→ "Update settings"

**List 1-5 capabilities:**
Just type them naturally, one per line or comma-separated!

Example:
"Me want Claude to send SMS, check message status, get account balance"

What do you want? 🤔"""

    def generate_mcp_server_boilerplate(
        self,
        api_name: str,
        api_description: str,
        auth_type: str,
        capabilities: List[str],
        api_docs_url: Optional[str] = None
    ) -> Dict[str, str]:
        """Generate MCP server boilerplate code.

        Args:
            api_name: Name of the API
            api_description: Description of what the API does
            auth_type: Type of authentication (api_key, oauth, basic, none, custom)
            capabilities: List of desired capabilities/tools
            api_docs_url: Optional documentation URL

        Returns:
            Dictionary with file names and their contents
        """
        # Sanitize API name for file/class names
        safe_name = api_name.lower().replace(" ", "_").replace("-", "_")
        class_name = "".join([word.capitalize() for word in safe_name.split("_")])

        # Generate package.json
        package_json = self._generate_package_json(safe_name, api_description)

        # Generate main server file
        server_ts = self._generate_server_ts(
            class_name,
            safe_name,
            api_description,
            auth_type,
            capabilities,
            api_docs_url
        )

        # Generate tsconfig.json
        tsconfig = self._generate_tsconfig()

        # Generate README
        readme = self._generate_readme(
            api_name,
            api_description,
            auth_type,
            capabilities,
            api_docs_url
        )

        # Generate .env.example
        env_example = self._generate_env_example(api_name, auth_type)

        return {
            "package.json": package_json,
            "src/index.ts": server_ts,
            "tsconfig.json": tsconfig,
            "README.md": readme,
            ".env.example": env_example
        }

    def _generate_package_json(self, safe_name: str, description: str) -> str:
        """Generate package.json content.

        Args:
            safe_name: Sanitized API name
            description: API description

        Returns:
            package.json content as string
        """
        package = {
            "name": f"@mcp/server-{safe_name}",
            "version": "0.1.0",
            "description": f"MCP server for {description}",
            "main": "dist/index.js",
            "type": "module",
            "scripts": {
                "build": "tsc",
                "prepare": "npm run build",
                "watch": "tsc --watch"
            },
            "keywords": ["mcp", "model-context-protocol", safe_name],
            "author": "",
            "license": "MIT",
            "dependencies": {
                "@modelcontextprotocol/sdk": "^1.0.0",
                "axios": "^1.6.0",
                "dotenv": "^16.0.0"
            },
            "devDependencies": {
                "@types/node": "^20.0.0",
                "typescript": "^5.3.0"
            }
        }
        return json.dumps(package, indent=2)

    def _generate_server_ts(
        self,
        class_name: str,
        safe_name: str,
        description: str,
        auth_type: str,
        capabilities: List[str],
        docs_url: Optional[str]
    ) -> str:
        """Generate TypeScript server code.

        Args:
            class_name: PascalCase class name
            safe_name: snake_case name
            description: API description
            auth_type: Authentication type
            capabilities: List of capabilities
            docs_url: Documentation URL

        Returns:
            TypeScript code as string
        """
        # Generate auth header code based on type
        auth_code = self._get_auth_code(auth_type)

        # Generate tool handlers
        tools_code = self._generate_tools_code(capabilities)

        code = f'''#!/usr/bin/env node

/**
 * MCP Server for {class_name}
 *
 * {description}
 * Generated by Ralph Mode MCP Generator
 */

import {{ Server }} from "@modelcontextprotocol/sdk/server/index.js";
import {{ StdioServerTransport }} from "@modelcontextprotocol/sdk/server/stdio.js";
import {{
  CallToolRequestSchema,
  ListToolsRequestSchema,
}} from "@modelcontextprotocol/sdk/types.js";
import axios, {{ AxiosInstance }} from "axios";
import * as dotenv from "dotenv";

// Load environment variables
dotenv.config();

/**
 * {class_name} MCP Server
 *
 * Provides Claude Code access to {description}
 */
class {class_name}Server {{
  private server: Server;
  private axiosInstance: AxiosInstance;

  constructor() {{
    this.server = new Server(
      {{
        name: "{safe_name}-server",
        version: "0.1.0",
      }},
      {{
        capabilities: {{
          tools: {{}},
        }},
      }}
    );

    // Initialize API client
    this.axiosInstance = axios.create({{
      baseURL: process.env.{safe_name.upper()}_API_BASE_URL || "https://api.example.com",
      headers: {{
{auth_code}
      }},
    }});

    this.setupToolHandlers();

    // Error handling
    this.server.onerror = (error) => console.error("[MCP Error]", error);
    process.on("SIGINT", async () => {{
      await this.server.close();
      process.exit(0);
    }});
  }}

  private setupToolHandlers() {{
    // List available tools
    this.server.setRequestHandler(ListToolsRequestSchema, async () => ({{
      tools: [
{self._generate_tools_list(capabilities)}
      ],
    }}));

    // Handle tool calls
    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {{
      try {{
        switch (request.params.name) {{
{tools_code}
          default:
            throw new Error(`Unknown tool: ${{request.params.name}}`);
        }}
      }} catch (error) {{
        return {{
          content: [
            {{
              type: "text",
              text: `Error: ${{error instanceof Error ? error.message : String(error)}}`,
            }},
          ],
        }};
      }}
    }});
  }}

{self._generate_tool_methods(capabilities, safe_name)}

  async run() {{
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error("{class_name} MCP server running on stdio");
  }}
}}

// Start the server
const server = new {class_name}Server();
server.run().catch(console.error);
'''
        return code

    def _get_auth_code(self, auth_type: str) -> str:
        """Generate authentication header code.

        Args:
            auth_type: Type of authentication

        Returns:
            Code snippet for auth headers
        """
        auth_type_lower = auth_type.lower()

        if auth_type_lower in ["api_key", "api key", "1"]:
            return '''        "Authorization": `Bearer ${process.env.API_KEY}`,
        "Content-Type": "application/json",'''
        elif auth_type_lower in ["oauth", "oauth 2.0", "2"]:
            return '''        // OAuth token will be added dynamically
        "Content-Type": "application/json",'''
        elif auth_type_lower in ["basic", "basic auth", "3"]:
            return '''        "Authorization": `Basic ${Buffer.from(process.env.API_USERNAME + ":" + process.env.API_PASSWORD).toString("base64")}`,
        "Content-Type": "application/json",'''
        elif auth_type_lower in ["none", "no auth", "4"]:
            return '''        "Content-Type": "application/json",'''
        else:
            return '''        // TODO: Add your custom authentication headers here
        "Content-Type": "application/json",'''

    def _generate_tools_list(self, capabilities: List[str]) -> str:
        """Generate the tools list for ListTools response.

        Args:
            capabilities: List of capability descriptions

        Returns:
            Code for tools array
        """
        tools = []
        for i, capability in enumerate(capabilities):
            tool_name = capability.lower().replace(" ", "_")
            tools.append(f'''        {{
          name: "{tool_name}",
          description: "{capability}",
          inputSchema: {{
            type: "object",
            properties: {{
              // TODO: Define input parameters
            }},
            required: [],
          }},
        }}''')
        return ",\n".join(tools)

    def _generate_tools_code(self, capabilities: List[str]) -> str:
        """Generate switch case handlers for tools.

        Args:
            capabilities: List of capabilities

        Returns:
            Switch case code
        """
        cases = []
        for capability in capabilities:
            tool_name = capability.lower().replace(" ", "_")
            method_name = "".join([word.capitalize() for word in tool_name.split("_")])
            cases.append(f'''          case "{tool_name}":
            return await this.handle{method_name}(request.params.arguments);''')
        return "\n\n".join(cases)

    def _generate_tool_methods(self, capabilities: List[str], safe_name: str) -> str:
        """Generate method implementations for each tool.

        Args:
            capabilities: List of capabilities
            safe_name: Safe API name

        Returns:
            Method implementations
        """
        methods = []
        for capability in capabilities:
            tool_name = capability.lower().replace(" ", "_")
            method_name = "".join([word.capitalize() for word in tool_name.split("_")])

            methods.append(f'''  private async handle{method_name}(args: any) {{
    // TODO: Implement {capability}
    // Example API call:
    // const response = await this.axiosInstance.get("/endpoint", {{ params: args }});

    return {{
      content: [
        {{
          type: "text",
          text: "TODO: Implement {capability} - check API docs and update this method",
        }},
      ],
    }};
  }}''')

        return "\n\n".join(methods)

    def _generate_tsconfig(self) -> str:
        """Generate tsconfig.json content.

        Returns:
            tsconfig.json content
        """
        config = {
            "compilerOptions": {
                "target": "ES2022",
                "module": "Node16",
                "moduleResolution": "Node16",
                "outDir": "./dist",
                "rootDir": "./src",
                "strict": True,
                "esModuleInterop": True,
                "skipLibCheck": True,
                "forceConsistentCasingInFileNames": True,
                "resolveJsonModule": True,
                "declaration": True
            },
            "include": ["src/**/*"],
            "exclude": ["node_modules", "dist"]
        }
        return json.dumps(config, indent=2)

    def _generate_readme(
        self,
        api_name: str,
        description: str,
        auth_type: str,
        capabilities: List[str],
        docs_url: Optional[str]
    ) -> str:
        """Generate README.md content.

        Args:
            api_name: API name
            description: API description
            auth_type: Authentication type
            capabilities: List of capabilities
            docs_url: Documentation URL

        Returns:
            README.md content
        """
        capabilities_list = "\n".join([f"- {cap}" for cap in capabilities])
        docs_section = f"\n\n## API Documentation\n\n{docs_url}" if docs_url else ""

        auth_setup = self._get_auth_setup_instructions(auth_type)

        return f"""# {api_name} MCP Server

MCP server for {description}

Generated by Ralph Mode MCP Generator 🚀

## Features

{capabilities_list}

## Installation

```bash
npm install
npm run build
```

## Configuration

1. Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

2. Fill in your credentials in `.env`
{auth_setup}

3. Add to your Claude Code configuration:

```json
{{
  "mcpServers": {{
    "{api_name.lower()}": {{
      "command": "node",
      "args": ["/path/to/this/server/dist/index.js"],
      "env": {{
        // Add your environment variables here
      }}
    }}
  }}
}}
```

## Usage

Once configured, Claude Code will have access to these tools:

{capabilities_list}

## Development

```bash
# Watch mode for development
npm run watch

# Build
npm run build
```

## Next Steps

1. Update the TODO comments in `src/index.ts` with actual API calls
2. Refer to the {api_name} API documentation for endpoint details
3. Test each tool thoroughly before deploying
{docs_section}

---

*Built with ❤️ using Ralph Mode*
"""

    def _get_auth_setup_instructions(self, auth_type: str) -> str:
        """Get setup instructions for auth type.

        Args:
            auth_type: Authentication type

        Returns:
            Setup instructions
        """
        auth_type_lower = auth_type.lower()

        if auth_type_lower in ["api_key", "api key", "1"]:
            return """
Get your API key from your API provider and add it to `.env`:
```
API_KEY=your_api_key_here
```"""
        elif auth_type_lower in ["oauth", "oauth 2.0", "2"]:
            return """
Set up OAuth 2.0 credentials:
1. Register your application with the API provider
2. Get your client ID and client secret
3. Add them to `.env`:
```
OAUTH_CLIENT_ID=your_client_id
OAUTH_CLIENT_SECRET=your_client_secret
```"""
        elif auth_type_lower in ["basic", "basic auth", "3"]:
            return """
Add your username and password to `.env`:
```
API_USERNAME=your_username
API_PASSWORD=your_password
```"""
        elif auth_type_lower in ["none", "no auth", "4"]:
            return "\nNo authentication required! Just set the base URL if needed."
        else:
            return "\nRefer to your API documentation for authentication setup."

    def _generate_env_example(self, api_name: str, auth_type: str) -> str:
        """Generate .env.example content.

        Args:
            api_name: API name
            auth_type: Authentication type

        Returns:
            .env.example content
        """
        safe_name = api_name.upper().replace(" ", "_").replace("-", "_")
        auth_type_lower = auth_type.lower()

        env_vars = [f"# {api_name} MCP Server Configuration\n"]
        env_vars.append(f"{safe_name}_API_BASE_URL=https://api.example.com\n")

        if auth_type_lower in ["api_key", "api key", "1"]:
            env_vars.append("API_KEY=your_api_key_here\n")
        elif auth_type_lower in ["oauth", "oauth 2.0", "2"]:
            env_vars.append("OAUTH_CLIENT_ID=your_client_id\n")
            env_vars.append("OAUTH_CLIENT_SECRET=your_client_secret\n")
        elif auth_type_lower in ["basic", "basic auth", "3"]:
            env_vars.append("API_USERNAME=your_username\n")
            env_vars.append("API_PASSWORD=your_password\n")

        return "".join(env_vars)

    def save_generated_files(
        self,
        files: Dict[str, str],
        output_dir: str = "./mcp-server"
    ) -> List[str]:
        """Save generated files to disk.

        Args:
            files: Dictionary of filename -> content
            output_dir: Output directory path

        Returns:
            List of created file paths
        """
        created_files = []
        output_path = Path(output_dir)

        for file_path, content in files.items():
            full_path = output_path / file_path

            # Create directories if needed
            full_path.parent.mkdir(parents=True, exist_ok=True)

            # Write file
            full_path.write_text(content)
            created_files.append(str(full_path))
            self.logger.info(f"Created {full_path}")

        return created_files

    def get_next_steps_message(self, output_dir: str, api_name: str) -> str:
        """Get message with next steps after generation.

        Args:
            output_dir: Where files were saved
            api_name: Name of the API

        Returns:
            Next steps message
        """
        return f"""*Server generated! Here's what to do next:* ✅

**Files created in `{output_dir}`:**
→ `package.json` - Node.js project config
→ `src/index.ts` - Your MCP server code
→ `tsconfig.json` - TypeScript config
→ `README.md` - Setup instructions
→ `.env.example` - Environment template

**Next steps:**

1️⃣ **Install dependencies:**
```
cd {output_dir}
npm install
```

2️⃣ **Configure your credentials:**
```
cp .env.example .env
# Edit .env with your API credentials
```

3️⃣ **Update the TODOs in src/index.ts:**
→ Replace placeholder API calls with real endpoints
→ Check {api_name} API docs for exact URLs

4️⃣ **Build the server:**
```
npm run build
```

5️⃣ **Test it:**
→ Add to your Claude Code config
→ Try the tools!

**Need help?**
→ Check the README.md file
→ Ask Ralph! Me here to help! 🧠

You did it! Now you have a custom MCP server! 🎉"""


# Singleton instance
_mcp_generator_instance = None


def get_mcp_generator() -> MCPGenerator:
    """Get the singleton MCP generator instance.

    Returns:
        MCPGenerator instance
    """
    global _mcp_generator_instance
    if _mcp_generator_instance is None:
        _mcp_generator_instance = MCPGenerator()
    return _mcp_generator_instance
