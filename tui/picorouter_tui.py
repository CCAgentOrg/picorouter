#!/usr/bin/env python3
"""PicoRouter TUI - Terminal User Interface."""

import os
import sys
import asyncio
from datetime import datetime

# Try to import textual, fall back to basic if not available
try:
    from textual.app import App, ComposeResult
    from textual.containers import Container, ScrollableContainer, Horizontal
    from textual.widgets import Header, Footer, Static, Input, Button, DataTable
    from textual.binding import Binding
    HAS_TEXTUAL = True
except ImportError:
    HAS_TEXTUAL = False


if HAS_TEXTUAL:
    class ChatMessage(Static):
        """Chat message widget."""
        
        def __init__(self, role: str, content: str):
            super().__init__()
            self.role = role
            self.content = content
        
        def render(self) -> str:
            prefix = "🤖" if self.role == "assistant" else "👤"
            return f"{prefix} {self.content}"
    
    
    class PicoRouterTUI(App):
        """PicoRouter Terminal UI."""
        
        TITLE = "PicoRouter TUI"
        BINDINGS = [
            Binding("q", "quit", "Quit"),
            Binding("c", "clear", "Clear"),
            Binding("m", "models", "Models"),
            Binding("s", "stats", "Stats"),
        ]
        
        CSS = """
        Screen {
            background: $surface;
        }
        #chat {
            height: 1fr;
            border: solid green;
        }
        #input {
            height: 3;
            border: solid blue;
        }
        #status {
            height: 3;
            dock: bottom;
            background: $surface-light;
        }
        """
        
        def __init__(self, base_url: str = "http://localhost:8080", api_key: str = None):
            super().__init__()
            self.base_url = base_url
            self.api_key = api_key
            self.messages = []
        
        def compose(self) -> ComposeResult:
            yield Header()
            yield ScrollableContainer(id="chat")
            yield Input(placeholder="Type message...", id="input")
            yield Static("Ready", id="status")
        
        def on_mount(self) -> None:
            """Called when app mounts."""
            self.query_one("#input").focus()
        
        def on_input_submit(self, event: Input.Submit) -> None:
            """Handle message submission."""
            message = event.value
            if not message:
                return
            
            # Add user message
            self.messages.append({"role": "user", "content": message})
            self.update_chat()
            
            # Clear input
            event.input.value = ""
            
            # Show thinking
            self.query_one("#status").update("🤔 Thinking...")
            
            # Get response
            asyncio.create_task(self.get_response(message))
        
        def update_chat(self) -> None:
            """Update chat display."""
            chat = self.query_one("#chat")
            chat.remove_children()
            
            for msg in self.messages[-20:]:  # Last 20 messages
                chat.mount(ChatMessage(msg["role"], msg["content"][:200]))
        
        async def get_response(self, message: str) -> None:
            """Get response from router."""
            try:
                from picorouter.sdk.picorouter import PicoRouter
                client = PicoRouter(self.base_url, self.api_key)
                result = await asyncio.to_thread(
                    client.chat, 
                    [{"role": "user", "content": message}]
                )
                
                content = result["choices"][0]["message"]["content"]
                self.messages.append({"role": "assistant", "content": content})
                self.update_chat()
                self.query_one("#status").update("Ready")
                
            except Exception as e:
                self.query_one("#status").update(f"Error: {e}")
        
        def action_quit(self) -> None:
            """Quit the app."""
            self.exit()
        
        def action_clear(self) -> None:
            """Clear chat."""
            self.messages = []
            self.update_chat()
        
        def action_models(self) -> None:
            """Show models."""
            try:
                from picorouter.sdk.picorouter import PicoRouter
                client = PicoRouter(self.base_url, self.api_key)
                models = client.models()
                self.messages.append({
                    "role": "assistant", 
                    "content": "Available models:\n" + 
                              "\n".join(f"  • {m['id']}" for m in models)
                })
                self.update_chat()
            except Exception as e:
                self.query_one("#status").update(f"Error: {e}")
        
        def action_stats(self) -> None:
            """Show stats."""
            try:
                from picorouter.sdk.picorouter import PicoRouter
                client = PicoRouter(self.base_url, self.api_key)
                stats = client.stats()
                self.messages.append({
                    "role": "assistant",
                    "content": f"Stats:\n  Requests: {stats.get('total_requests', 0)}\n  Tokens: {stats.get('total_tokens', 0)}\n  Cost: ${stats.get('total_cost_usd', 0):.4f}"
                })
                self.update_chat()
            except Exception as e:
                self.query_one("#status").update(f"Error: {e}")


def run_tui(base_url: str = "http://localhost:8080", api_key: str = None):
    """Run the TUI."""
    if not HAS_TEXTUAL:
        print("❌ textual not installed. Run: pip install textual")
        print("   Falling back to basic CLI chat...")
        basic_chat(base_url, api_key)
        return
    
    app = PicoRouterTUI(base_url, api_key)
    app.run()


def basic_chat(base_url: str, api_key: str = None):
    """Basic chat if textual not available."""
    from picorouter.sdk.picorouter import PicoRouter
    client = PicoRouter(base_url, api_key)
    
    print("🧩 PicoRouter Chat (type 'quit' to exit)")
    print("-" * 40)
    
    while True:
        try:
            msg = input("👤 You: ")
            if msg.lower() in ["quit", "exit"]:
                break
            
            if not msg.strip():
                continue
            
            print("🤖 Bot: ", end="", flush=True)
            resp = client.chat_simple(msg)
            print(resp[:200])
            print()
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="PicoRouter TUI")
    parser.add_argument("--url", default="http://localhost:8080", help="PicoRouter URL")
    parser.add_argument("--api-key", help="API key")
    
    args = parser.parse_args()
    run_tui(args.url, args.api_key)
