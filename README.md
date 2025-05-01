# Claude 3.7 Sonnet MCP Interface

This project enables powerful, LLM-agnostic interactions with [Claude 3.7 Sonnet](https://www.anthropic.com/index/claude-3), either via the Claude Desktop (MCP GUI) or directly through a command-line client using [AWS Bedrock](https://aws.amazon.com/bedrock/) and the [MCP protocol](https://github.com/ai-sdk/mcp).

---

## 🧭 Options for Usage

You can interact with Claude in **two ways**:

---

## 🖥️ 1. Using Claude Desktop (GUI with MCP Server)

Claude Desktop provides a graphical interface for working with Claude via the MCP protocol. It is ideal for users who want a visual tool experience.

### ✅ Features

- GUI-based interaction with Claude
- Tool registration and calls via local or remote servers
- Plug-and-play tool development and testing

### 🚀 Usage

1. **Start Claude Desktop**
   - Run the application
   - Point it to your local or remote MCP-compatible tool server ( `fastmcp install server_name.py` )

2. **Connect a tool server**
   - Claude Desktop uses MCP’s `stdio` or `http` transport to connect to tool providers.

3. **Start chatting**
   - You can test tool calling, observe Claude's responses, and debug tool output.

📦 For more info, visit: [https://github.com/ai-sdk/mcp](https://github.com/ai-sdk/mcp)

---

## 🧑‍💻 2. Using MCP Client Directly (CLI via Bedrock)

This CLI tool connects to Claude through AWS Bedrock and automatically handles tool calling using the MCP protocol.

### ✨ Features

- CLI-driven interaction with Claude 3.7 Sonnet
- Automatic tool discovery via MCP
- Tool call execution and response routing
- Rich UI with markdown, syntax highlighting, and spinners
- Lightweight and extensible

### 📦 Setup

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
git clone https://github.com/your-username/claude-mcp-client.git
cd claude-mcp-client
uv venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
uv pip install -r requirements.txt
```

Create a `.env` file in the root:

```env
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=us-east-1
AUTHTOKEN=bltsomething
BRAND_KIT_UID=cssomething
```

> 🧠 Model used: `us.anthropic.claude-3-7-sonnet-20250219-v1:0`

### 🚀 Running the Client

```bash
python client.py ./brand-kit/knowledge-vault/crud.py
```

### Example Tool Server

```python
# tool_server.py
from mcp.server.fastmcp import FastMCP 
server = FastMCP()
@server.tool()
class AddTool(Tool):
    name = "add"
    description = "Adds two numbers"
    input_schema = {"a": "number", "b": "number"}

    async def call(self, input):
        return input["a"] + input["b"]

if __name__ == "__main__":
    server.run()
```


### 🧠 Interaction Flow

- The CLI maintains a conversation history (configurable)
- Claude can detect when a tool is needed and call it automatically
- Tool responses are routed back to Claude for follow-up
- Everything is streamed and displayed beautifully in your terminal

### 💡 Type `quit` anytime to exit.

---

## 🛠 Architecture Overview

```
Claude (via AWS Bedrock)
        |
      Client.py
        |
    ┌────────────┐
    │ MCP Server │  <── Tool: Python or JS
    └────────────┘
```

---

## 🧹 Cleanup

The client ensures graceful shutdown using `AsyncExitStack` and `aclose()` to clean up all sessions.

---

## 🛡 License

MIT License

---

## 🙏 Credits

- [Anthropic Claude](https://www.anthropic.com/)
- [AWS Bedrock](https://aws.amazon.com/bedrock/)
- [MCP Protocol](https://github.com/ai-sdk/mcp)
- [Textualize Rich](https://github.com/Textualize/rich)
