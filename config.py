from pathlib import Path
import logging
import os
from dotenv import load_dotenv

load_dotenv()

# header api key
api_key = os.getenv("API_KEY")

# Oracle Database credentials
uname = os.getenv("DB_USERNAME")
pwd = os.getenv("DB_PASSWORD")

# OCI DB Schema
schema = os.getenv("SCHEMA")

wltpwd = os.getenv("WALLET_PASSWORD")

# Oracle Wallet credentials
BASE_DIR = Path(__file__).resolve().parent  # project root
WALLET_DIR_NAME = os.getenv("WALLET_DIR", "Wallet_CLOUDEX")
wallet_path = str((BASE_DIR / WALLET_DIR_NAME).resolve())
cdir = wallet_path if os.path.isdir(wallet_path) else None
wltloc = wallet_path if os.path.isdir(wallet_path) else None
dsn = os.getenv("DB_DSN", "(description=(retry_count=20)(retry_delay=3)(address=(protocol=tcps)(port=1522)(host=adb.us-phoenix-1.oraclecloud.com))(connect_data=(service_name=your_service_name_medium.adb.oraclecloud.com))(security=(ssl_server_dn_match=yes)))")


# MCP Server configuration
MCP_SERVER_LABEL = os.getenv("MCP_SERVER_LABEL", "tech_support_mcp")
MCP_SERVER_DESCRIPTION = os.getenv("MCP_SERVER_DESCRIPTION", "Enterprise Technical Support & Oracle Autonomous Database MCP Server")
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8000/sse")
MCP_REQUIRE_APPROVAL = os.getenv("MCP_REQUIRE_APPROVAL", "never")