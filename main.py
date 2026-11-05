import atexit
import os
import socket
import subprocess
import sys
import time
import urllib.parse
from dotenv import load_dotenv
from langfuse.openai import OpenAI
from langfuse import observe, propagate_attributes
from prompt import system_promt
from config import MCP_SERVER_LABEL, MCP_SERVER_DESCRIPTION, MCP_SERVER_URL, MCP_REQUIRE_APPROVAL, BASE_DIR

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OCI_API_KEY_ONE"),
    base_url="https://inference.generativeai.us-phoenix-1.oci.oraclecloud.com/openai/v1",
    project=os.getenv("PROJECT_OCID")
)

_mcp_process = None

def stop_mcp_server():
    """Terminate the local MCP server subprocess if started by this script."""
    global _mcp_process
    if _mcp_process and _mcp_process.poll() is None:
        print("\n[Shutting down local MCP server...]")
        _mcp_process.terminate()
        try:
            _mcp_process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            _mcp_process.kill()
        _mcp_process = None

atexit.register(stop_mcp_server)

def start_mcp_server_if_needed(mcp_url: str):
    """Start local MCP server on port 8000 automatically if not currently running."""
    global _mcp_process
    if not mcp_url:
        return
    
    port = 8000
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.5)
    is_running = (sock.connect_ex(("127.0.0.1", port)) == 0)
    sock.close()

    if not is_running:
        server_script = os.path.join(BASE_DIR, "mcp_server.py")
        if os.path.exists(server_script):
            print(f"[Starting local MCP server on port {port} (Streamable HTTP transport)...]")
            _mcp_process = subprocess.Popen(
                [sys.executable, server_script, "--transport", "streamable-http", "--port", str(port)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            for _ in range(25):
                time.sleep(0.2)
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.5)
                if sock.connect_ex(("127.0.0.1", port)) == 0:
                    sock.close()
                    print("[MCP server started successfully and ready.]\n")
                    return
                sock.close()
            print("[Warning: MCP server took longer than expected to initialize.]\n")

def create_cov():
    conversation = client.conversations.create()
    print("Conversation ID: " + conversation.id)
    return conversation.id

def delete_cov(conv_id):
    return client.conversations.delete(conversation_id=conv_id)

def get_tools():
    """Build the MCP tools list if MCP_SERVER_URL is configured."""
    mcp_url = os.getenv("MCP_SERVER_URL", MCP_SERVER_URL)
    if not mcp_url:
        return None
    
    # Auto-start local MCP server on port 8000
    start_mcp_server_if_needed(mcp_url)
    
    # Normalize URL to ensure it points to the /sse endpoint
    clean_url = mcp_url.strip()
    if not clean_url.endswith("/sse") and not clean_url.endswith("/mcp"):
        clean_url = clean_url.rstrip("/") + "/sse"
    
    return [
        {
            "type": "mcp",
            "server_label": os.getenv("MCP_SERVER_LABEL", MCP_SERVER_LABEL),
            "server_description": os.getenv("MCP_SERVER_DESCRIPTION", MCP_SERVER_DESCRIPTION),
            "server_url": clean_url,
            "require_approval": os.getenv("MCP_REQUIRE_APPROVAL", MCP_REQUIRE_APPROVAL),
        }
    ]

@observe()
def chat(conv_id, session_id="test_session" + str(time.time()), user_id="11223435"):
    with propagate_attributes(session_id=session_id, user_id=user_id):
        print("\n Hala: Hello! I am Hala, your technical support agent. How can I help you today?\n")    
        tools = get_tools()
        while(True):
            user_input = input("User: ")
            if not user_input.strip():
                continue
            if user_input.lower() == "exit":
                if conv_id:
                    print("Deleting conversation...")
                    temp = delete_cov(conv_id)
                    print("Is deleted: " + str(temp.deleted))
                print("Exiting...")
                break
            
            start = time.time()
            try:
                kwargs = {
                    "model": "google.gemini-2.5-pro",
                    "input": user_input,
                    "conversation": conv_id if conv_id else None,
                    "instructions": system_promt,
                    "name": "techSupport",
                }
                if tools:
                    kwargs["tools"] = tools

                response = client.responses.create(**kwargs)
                end = time.time()
                t = end - start
                print("\nHala:", response.output_text)
                print(f"[Response time: {t:.2f}s]\n")
            except Exception as e:
                print(f"\n[Error generating response: {e}]\n")

def main():
    conv_id = ""
    try:
        if input("Do you want to create a conversation? (y/n): ").lower() == "y":
            conv_id = create_cov()
        chat(conv_id)
    finally:
        stop_mcp_server()

if __name__ == "__main__":
    main()

