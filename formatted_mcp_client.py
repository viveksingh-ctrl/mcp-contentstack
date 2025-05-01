import asyncio
import json
import sys
import os
from typing import Optional, Dict, List, Any
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import boto3
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt
from rich.table import Table
from rich.box import ROUNDED
from rich.live import Live
from rich.spinner import Spinner
from rich.layout import Layout
from rich.syntax import Syntax
from rich import print as rprint
import time

# Load environment variables
load_dotenv()

# Initialize Rich console
console = Console()

class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        
        # Initialize AWS Bedrock client
        self.bedrock_runtime = boto3.client('bedrock-runtime', region_name = 'us-east-1')
        self.model_id = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"  # Claude 3.7 Sonnet model ID
        
        # Conversation history - maintain a list of messages for context
        self.message_history = []
        self.max_history = 5  # Keep context of last 5 exchanges
        
        # Rich UI components
        self.console = console
        
    def display_welcome(self):
        """Display an attractive welcome message"""
        # Clear the screen
        os.system('cls' if os.name == 'nt' else 'clear')
        
        # Create title panel
        title_panel = Panel(
            "[bold blue]Claude 3.7 Sonnet MCP Client[/bold blue]", 
            subtitle="[italic]Powered by Contentstack & AWS Bedrock[/italic]",
            border_style="blue"
        )
        
        # Create info table
        info_table = Table(show_header=False, box=ROUNDED, expand=True, border_style="dim")
        info_table.add_column("Key", style="green")
        info_table.add_column("Value")
        info_table.add_row("Model", f"[yellow]{self.model_id}[/yellow]")  
        info_table.add_row("Context Window", f"[yellow]{self.max_history} exchanges[/yellow]")
        info_table.add_row("Exit Command", "[yellow]quit[/yellow]")
        
        # Display welcome components
        self.console.print(title_panel)
        self.console.print(info_table)
        self.console.print("\n[bold]Type your queries below. Type [yellow]quit[/yellow] to exit.[/bold]\n")

    async def connect_to_server(self, server_script_path: str):
        """Connect to an MCP server
        Args:
            server_script_path: Path to the server script (.py or .js)
        """
        with self.console.status("[bold green]Connecting to MCP server...", spinner="dots"):
            is_python = server_script_path.endswith('.py')
            is_js = server_script_path.endswith('.js')
            if not (is_python or is_js):
                raise ValueError("Server script must be a .py or .js file")
            
            command = "python" if is_python else "node"
            server_params = StdioServerParameters(
                command=command,
                args=[server_script_path],
                env=None
            )
            
            stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
            self.stdio, self.write = stdio_transport
            self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
            await self.session.initialize()
            
            # List available tools
            response = await self.session.list_tools()
            self.tools = response.tools

        # Show connected tools in a nice table
        tools_table = Table(title="Available Tools", box=ROUNDED, border_style="green")
        tools_table.add_column("Tool Name", style="cyan")
        tools_table.add_column("Description", style="white")
        
        for tool in self.tools:
            tools_table.add_row(tool.name, tool.description)
        
        self.console.print(tools_table)

    def invoke_claude_with_bedrock(self, messages: List[Dict], tools: List[Dict] = None) -> Dict:
        """Call Claude 3.7 Sonnet through AWS Bedrock"""
        # Make sure all content is serializable as JSON
        processed_messages = []
        
        for msg in messages:
            if isinstance(msg["content"], list):
                # For messages with content as a list of blocks
                processed_content = []
                for block in msg["content"]:
                    # Process each block to ensure it's properly formatted
                    processed_block = dict(block)  # Make a copy
                    if "content" in processed_block and not isinstance(processed_block["content"], (str, int, float, bool, type(None))):
                        processed_block["content"] = str(processed_block["content"])
                    processed_content.append(processed_block)
                processed_messages.append({"role": msg["role"], "content": processed_content})
            else:
                # For messages with simple string content
                processed_messages.append(msg)
        
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "messages": processed_messages,
            "system": '''You are a helpful assistant, whose task is to help out the user with common knowledge and use of tools. 
                        In simple words, answer to the best of your knowledge and use tools ONLY WHEN REQUIRED.
                     '''
        }
        
        # Add tools if provided
        if tools:
            request_body["tools"] = tools
        
        try:
            response = self.bedrock_runtime.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body)
            )
            response_body = json.loads(response['body'].read().decode('utf-8'))
            return response_body
        except Exception as e:
            error_msg = f"Error invoking Claude: {str(e)}"
            self.console.print(f"[bold red]{error_msg}[/bold red]")
            # Print part of the request for debugging
            self.console.print(f"[dim]Request that caused error: {json.dumps(request_body)[:300]}...[/dim]")
            raise Exception(error_msg)

    def parse_claude_response(self, response: Dict) -> tuple:
        """Parse Claude's response and extract text and tool uses"""
        content = response.get('content', [])
        texts = []
        tool_uses = []
        
        for item in content:
            if item['type'] == 'text':
                texts.append(item['text'])
            elif item['type'] == 'tool_use':
                tool_uses.append(item)
        
        return texts, tool_uses

    def maintain_conversation_history(self, role: str, content) -> None:
        """Add a message to the conversation history and trim if needed"""
        self.message_history.append({"role": role, "content": content})
        
        # Keep only the most recent exchanges to limit context window
        if len(self.message_history) > self.max_history * 2:  # Each exchange has 2 messages
            # Remove oldest exchanges (both user and assistant messages)
            self.message_history = self.message_history[-(self.max_history * 2):]

    async def process_query(self, query: str) -> str:
        """Process a query using Claude and available tools"""
        # Add the new query to message history
        self.maintain_conversation_history("user", query)
        
        # Use the maintained history for context
        messages = self.message_history.copy()
        
        response = await self.session.list_tools()
        available_tools = [{
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.inputSchema
        } for tool in response.tools]
        
        final_text = []
        
        try:
            # Initial Claude API call through Bedrock
            with self.console.status("[bold green]Claude is thinking...", spinner="dots"):
                claude_response = self.invoke_claude_with_bedrock(messages, available_tools)
            
            # Process response and handle tool calls
            texts, tool_uses = self.parse_claude_response(claude_response)
            final_text.extend(texts)
            
            # Save Claude's response to append to messages
            assistant_message_content = claude_response.get('content', [])
            self.maintain_conversation_history("assistant", assistant_message_content)
            
            # Handle any tool calls
            if tool_uses:
                # Process each tool use
                for tool_use in tool_uses:
                    tool_name = tool_use['name'] 
                    tool_args = tool_use['input']
                    tool_id = tool_use['id']
                    try:
                        # Execute tool call
                        with self.console.status(f"[bold yellow]Executing tool {tool_name}...", spinner="dots"):
                            result = await self.session.call_tool(tool_name, tool_args)
                            # Handle different response types
                            if hasattr(result, 'content'):
                                # Convert content to string if it's not already
                                tool_result = str(result.content) if result.content is not None else ""
                            else:
                                # If no content attribute, convert the whole result to string
                                tool_result = str(result)
                        
                        # Create nice display for tool call
                        tool_call_panel = Panel(
                            f"[bold]Tool:[/bold] {tool_name}\n[bold]Arguments:[/bold] {json.dumps(tool_args, indent=2)}", 
                            title="Tool Call", 
                            border_style="yellow"
                        )
                        
                        # Create nice display for tool result
                        tool_result_panel = Panel(
                            tool_result, 
                            title="Tool Result", 
                            border_style="green"
                        )
                        
                        self.console.print(tool_call_panel)
                        self.console.print(tool_result_panel)
                        
                        # Log the tool use and result for final output collection
                        final_text.append(f"[Tool Call: {tool_name}]")
                        final_text.append(f"[Tool Result: {tool_result}]")
                        
                        # Add tool result to messages - follow Bedrock API format
                        tool_result_message = {
                            "role": "user",
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": tool_id,
                                    "content": tool_result
                                }
                            ]
                        }
                        
                        # Add tool result to history
                        self.message_history.append(tool_result_message)
                        
                        # Get next response from Claude with updated history
                        with self.console.status("[bold green]Claude is processing the tool result...", spinner="dots"):
                            claude_response = self.invoke_claude_with_bedrock(self.message_history, available_tools)
                        
                        follow_up_texts, more_tool_uses = self.parse_claude_response(claude_response)
                        
                        # Save Claude's follow-up response
                        assistant_message_content = claude_response.get('content', [])
                        self.maintain_conversation_history("assistant", assistant_message_content)
                        
                        final_text.extend(follow_up_texts)
                        
                        # Handle any additional tool uses from the follow-up response
                        if more_tool_uses:
                            self.console.print("[dim]Additional tool calls detected but not processed in this response[/dim]")
                            final_text.append("[Additional tool calls detected but not processed in this response]")
                        
                    except Exception as e:
                        error_msg = f"Error executing tool {tool_name}: {str(e)}"
                        self.console.print(f"[bold red]{error_msg}[/bold red]")
                        final_text.append(f"[Error: {error_msg}]")
                        
                        # Add error result to messages - follow Bedrock API format
                        tool_error_message = {
                            "role": "user",
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": tool_id,
                                    "content": error_msg
                                }
                            ]
                        }
                        
                        # Add error to history
                        self.message_history.append(tool_error_message)
                        
                        # Get next response from Claude
                        with self.console.status("[bold green]Claude is handling the error...", spinner="dots"):
                            claude_response = self.invoke_claude_with_bedrock(self.message_history, available_tools)
                        
                        texts, _ = self.parse_claude_response(claude_response)
                        
                        # Save Claude's follow-up response
                        assistant_message_content = claude_response.get('content', [])
                        self.maintain_conversation_history("assistant", assistant_message_content)
                        
                        final_text.extend(texts)
        
        except Exception as e:
            return f"Error processing query: {str(e)}"
            
        return "\n".join(final_text)

    async def chat_loop(self):
        """Run an interactive chat loop"""
        # Display welcome banner
        self.display_welcome()
        
        conversation_count = 0
        
        while True:
            try:
                query = Prompt.ask("\n[bold cyan]You[/bold cyan]")
                if query.lower() == 'quit':
                    break
                
                # Show a divider for better readability
                if conversation_count > 0:
                    self.console.print("[dim]" + "-" * 80 + "[/dim]")
                
                # Process the query
                response = await self.process_query(query)
                
                # Display the response in a nice panel with markdown support
                response_md = Markdown(response)
                response_panel = Panel(
                    response_md, 
                    title="[bold purple]Claude[/bold purple]", 
                    border_style="purple"
                )
                self.console.print(response_panel)
                
                conversation_count += 1
                
            except Exception as e:
                self.console.print(f"[bold red]Error:[/bold red] {str(e)}")

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()

async def main():
    if len(sys.argv) < 2:
        console.print("[bold red]Usage: python client.py <path_to_server_script>[/bold red]")
        sys.exit(1)
    
    client = MCPClient()
    try:
        await client.connect_to_server(sys.argv[1])
        await client.chat_loop()
    finally:
        await client.cleanup()
        console.print("\n[bold green]Thank you for using Claude MCP Client! Goodbye![/bold green]")

if __name__ == "__main__":
    asyncio.run(main())