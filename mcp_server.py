import argparse
import json
import logging
import uuid
import datetime
from mcp.server.fastmcp import FastMCP
from db_manager import db_manager
from config import schema

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("TechSupportMCP")

# Initialize FastMCP Server
mcp = FastMCP(
    "Enterprise Tech Support & Oracle Autonomous DB Server",
    instructions="Provides enterprise technical support diagnostics, IT troubleshooting, and Oracle Autonomous Database tools.",
    host="0.0.0.0",
    port=8000
)

# Built-in IT Knowledge Base
IT_KNOWLEDGE_BASE = [
    {
        "category": "Performance",
        "keywords": ["slow", "freezing", "lag", "high memory", "cpu", "disk"],
        "issue": "Device / PC is running very slow",
        "troubleshooting_steps": [
            "1. Restart the device to clear temporary cache and background processes.",
            "2. Open Task Manager (Ctrl + Shift + Esc) and check for high CPU, Memory, or Disk usage.",
            "3. Close unused heavy background applications and browser tabs.",
            "4. Check available storage on C: drive and ensure at least 15% free space.",
            "5. Run a full antivirus/antimalware scan.",
            "6. Check Windows Update for pending system updates."
        ]
    },
    {
        "category": "Network",
        "keywords": ["wifi", "wi-fi", "internet", "network", "offline", "dns", "connection"],
        "issue": "Cannot connect to Wi-Fi or local network",
        "troubleshooting_steps": [
            "1. Toggle Wi-Fi adapter off and on.",
            "2. Verify Airplane Mode is turned OFF.",
            "3. Forget the Wi-Fi network and reconnect with corporate credentials.",
            "4. Flush DNS: Open Command Prompt as admin and run 'ipconfig /flushdns' followed by 'ipconfig /renew'.",
            "5. Restart your wireless router/access point if working remotely.",
            "6. Update network adapter drivers in Device Manager."
        ]
    },
    {
        "category": "Hardware / Peripherals",
        "keywords": ["keyboard", "mouse", "trackpad", "usb", "monitor", "display"],
        "issue": "Keyboard, mouse, or peripheral device not responding",
        "troubleshooting_steps": [
            "1. Disconnect and securely reconnect the USB cable or wireless dongle.",
            "2. Try a different USB port directly on the motherboard/laptop (avoid unpowered hubs).",
            "3. If using Bluetooth, verify Bluetooth is active and re-pair the device.",
            "4. Check or replace device batteries.",
            "5. Test the peripheral on another machine to rule out hardware failure."
        ]
    },
    {
        "category": "Power & Battery",
        "keywords": ["battery", "charger", "charging", "power", "plugged in not charging"],
        "issue": "Laptop battery not charging or draining fast",
        "troubleshooting_steps": [
            "1. Inspect the charging adapter, cable, and wall outlet for physical damage.",
            "2. Check charging port for dust/debris and clean carefully if needed.",
            "3. Disconnect power, hold power button for 15 seconds to perform a static discharge, then reconnect.",
            "4. Verify battery health in OS power settings or OEM diagnostics (e.g. Dell Command / Lenovo Vantage).",
            "5. If 'plugged in, not charging' persists, escalate for battery replacement."
        ]
    },
    {
        "category": "VPN & Remote Access",
        "keywords": ["vpn", "cisco", "anyconnect", "fortinet", "remote desktop", "rdp"],
        "issue": "VPN connection failure or cannot access intranet",
        "troubleshooting_steps": [
            "1. Verify active internet connection before initiating VPN.",
            "2. Confirm correct VPN gateway address and multi-factor authentication (MFA) approval.",
            "3. Restart the VPN client software and check for client version updates.",
            "4. Disconnect any conflicting third-party VPNs or proxies.",
            "5. Verify your corporate credentials have not expired."
        ]
    },
    {
        "category": "Email & Collaboration",
        "keywords": ["outlook", "email", "teams", "slack", "office 365", "mailbox"],
        "issue": "Outlook / Teams login issues or emails not syncing",
        "troubleshooting_steps": [
            "1. Restart Outlook / Teams and verify webmail access via browser (outlook.office.com).",
            "2. Check Microsoft 365 service status for regional outages.",
            "3. Clear Teams cache in %appdata%\\Microsoft\\Teams.",
            "4. Use Outlook in Safe Mode ('outlook.exe /safe') to check if add-ins cause crashes.",
            "5. If credentials fail repeatedly, contact IT Helpdesk for password reset."
        ]
    }
]


# ==========================================
# Tool 1: List Database Tables
# ==========================================
@mcp.tool()
def list_tables() -> str:
    """
    List all tables available in the current Oracle Autonomous Database schema.
    Returns a JSON string containing the list of table names.
    """
    try:
        if schema:
            sql = "SELECT table_name FROM all_tables WHERE owner = UPPER(:schema) ORDER BY table_name"
            res = db_manager.run_query(sql, {"schema": schema.strip()})
        else:
            sql = "SELECT table_name FROM user_tables ORDER BY table_name"
            res = db_manager.run_query(sql)

        if res.get("is_data_found"):
            tables = [row["TABLE_NAME"] for row in res["data"] if "TABLE_NAME" in row]
            return json.dumps({"schema": schema or "CURRENT_USER", "tables": tables, "count": len(tables)}, indent=2)
        return json.dumps({"error": res.get("data", "No tables found")})
    except Exception as e:
        logger.error(f"Error in list_tables: {e}")
        return json.dumps({"error": str(e)})


# ==========================================
# Tool 2: Describe Database Table
# ==========================================
@mcp.tool()
def describe_table(table_name: str) -> str:
    """
    Get the structure, column names, data types, lengths, and nullability for a specific table in Oracle DB.
    
    Args:
        table_name: The name of the table to describe (e.g. 'EMPLOYEES', 'APP_USERS', 'JOBS_JOB_DETAILS').
    """
    clean_table_name = table_name.strip().upper()
    try:
        if schema:
            sql = """
            SELECT column_name, data_type, data_length, nullable
            FROM all_tab_columns
            WHERE owner = UPPER(:schema) AND table_name = :tbl
            ORDER BY column_id
            """
            res = db_manager.run_query(sql, {"schema": schema.strip(), "tbl": clean_table_name})
        else:
            sql = """
            SELECT column_name, data_type, data_length, nullable
            FROM user_tab_columns
            WHERE table_name = :tbl
            ORDER BY column_id
            """
            res = db_manager.run_query(sql, {"tbl": clean_table_name})

        if res.get("is_data_found") and res.get("data"):
            return json.dumps({
                "schema": schema or "CURRENT_USER",
                "table_name": clean_table_name,
                "columns": res["data"]
            }, indent=2)
        return json.dumps({"error": f"Table '{clean_table_name}' not found or has no columns."})
    except Exception as e:
        logger.error(f"Error in describe_table: {e}")
        return json.dumps({"error": str(e)})


# ==========================================
# Tool 3: Execute SELECT Query
# ==========================================
@mcp.tool()
def execute_query(sql_query: str) -> str:
    """
    Execute a read-only SELECT SQL query against Oracle Autonomous Database and return formatted results.
    
    Args:
        sql_query: The SQL SELECT statement to execute (e.g. 'SELECT * FROM EMPLOYEES WHERE ROWNUM <= 5').
    """
    cleaned_query = sql_query.strip()
    if not cleaned_query.upper().startswith("SELECT"):
        return json.dumps({"error": "Security restriction: Only SELECT queries are permitted via this tool."})

    try:
        res = db_manager.run_query(cleaned_query)
        if res.get("is_data_found"):
            return json.dumps({
                "success": True,
                "rows_count": len(res.get("data", [])),
                "columns": res.get("columns", []),
                "data": res.get("data", [])
            }, indent=2, default=str)
        return json.dumps({"success": False, "message": res.get("data", "No data returned.")})
    except Exception as e:
        logger.error(f"Error in execute_query: {e}")
        return json.dumps({"error": str(e)})


# ==========================================
# Tool 4: Search IT Knowledge Base
# ==========================================
@mcp.tool()
def search_it_knowledge_base(query: str) -> str:
    """
    Search the internal IT support knowledge base for solutions to common technical issues (slow PC, Wi-Fi, peripherals, battery, VPN, Outlook).
    
    Args:
        query: Keywords or description of the issue (e.g. 'wifi not working', 'computer slow', 'vpn failed').
    """
    query_lower = query.lower()
    matches = []
    
    for item in IT_KNOWLEDGE_BASE:
        if (query_lower in item["category"].lower() or 
            query_lower in item["issue"].lower() or 
            any(kw in query_lower for kw in item["keywords"])):
            matches.append(item)
    
    if not matches:
        words = query_lower.split()
        for item in IT_KNOWLEDGE_BASE:
            if any(w in item["issue"].lower() or any(w in kw for kw in item["keywords"]) for w in words):
                if item not in matches:
                    matches.append(item)

    if matches:
        return json.dumps({
            "matched_articles_count": len(matches),
            "results": matches
        }, indent=2)
    
    return json.dumps({
        "message": f"No specific knowledge base article found for '{query}'. Please advise the user to contact the IT department at support@yourcompany.com."
    })



# ==========================================
# Tool 5: Lookup Employee Contact / Status
# ==========================================
@mcp.tool()
def lookup_employee_contact(search_term: str) -> str:
    """
    Lookup an employee or IT user by name, ID, or email in the database.
    
    Args:
        search_term: Name, ID, or email of the employee.
    """
    clean_term = search_term.strip()
    target_schema = schema.strip() if schema else ""
    emp_table = f"{target_schema}.EMPLOYEES" if target_schema else "EMPLOYEES"
    user_table = f"{target_schema}.APP_USERS" if target_schema else "APP_USERS"
    
    try:
        # Search EMPLOYEES table
        emp_sql = f"""
        SELECT ID, FULL_NAME, EMAIL, JOB_TITLE, PHONE_NUMBER, LOCATION, SKILLS
        FROM {emp_table}
        WHERE UPPER(FULL_NAME) LIKE UPPER('%' || :term || '%') 
           OR UPPER(EMAIL) LIKE UPPER('%' || :term || '%')
           OR TO_CHAR(ID) = :term
        """
        res = db_manager.run_query(emp_sql, {"term": clean_term})
        if res.get("is_data_found") and res.get("data"):
            return json.dumps({
                "found": True,
                "source": "EMPLOYEES",
                "employees": res["data"]
            }, indent=2, default=str)
        
        # Search APP_USERS table
        user_sql = f"""
        SELECT USER_ID, FULL_NAME, EMAIL, PHONE, ROLE_NAME, STATUS
        FROM {user_table}
        WHERE UPPER(FULL_NAME) LIKE UPPER('%' || :term || '%') 
           OR UPPER(EMAIL) LIKE UPPER('%' || :term || '%')
           OR TO_CHAR(USER_ID) = :term
        """
        u_res = db_manager.run_query(user_sql, {"term": clean_term})
        if u_res.get("is_data_found") and u_res.get("data"):
            return json.dumps({
                "found": True,
                "source": "APP_USERS",
                "users": u_res["data"]
            }, indent=2, default=str)

        return json.dumps({"found": False, "message": f"No employee or user records matching '{clean_term}'."})
    except Exception as e:
        logger.error(f"Error looking up employee: {e}")
        return json.dumps({"error": str(e)})


# ==========================================
# Tool 6: Submit IT Support Ticket
# ==========================================
@mcp.tool()
def submit_it_ticket(
    employee_name: str,
    employee_email: str,
    issue_category: str,
    issue_description: str,
    priority: str = "Medium"
) -> str:
    """
    Submit and generate an official IT support ticket for unresolved technical issues.
    
    Args:
        employee_name: Name of the employee experiencing the issue.
        employee_email: Contact email address of the employee.
        issue_category: Category (e.g. 'Hardware', 'Network', 'Software', 'Access', 'Security').
        issue_description: Detailed explanation of the problem and steps already attempted.
        priority: Priority level ('Low', 'Medium', 'High', 'Critical').
    """
    ticket_id = f"TICK-{datetime.date.today().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    created_at = datetime.datetime.now().isoformat()
    
    ticket_data = {
        "ticket_id": ticket_id,
        "status": "OPEN",
        "created_at": created_at,
        "employee_name": employee_name,
        "employee_email": employee_email,
        "category": issue_category,
        "priority": priority,
        "description": issue_description,
        "assigned_to": "IT Support Tier 2",
        "estimated_response_time": "2 to 4 business hours"
    }

    logger.info(f"Support ticket created: {ticket_id} for {employee_email}")
    return json.dumps({
        "success": True,
        "message": f"IT Support Ticket {ticket_id} has been logged successfully.",
        "ticket": ticket_data
    }, indent=2)


def run_http_server(host: str = "0.0.0.0", port: int = 8000):
    """Run an HTTP server that supports Streamable HTTP MCP transport on /, /mcp, and /sse."""
    import uvicorn
    from starlette.applications import Starlette
    from starlette.routing import Route
    from mcp.server.fastmcp.server import StreamableHTTPSessionManager, StreamableHTTPASGIApp
    
    if mcp._session_manager is None:
        mcp._session_manager = StreamableHTTPSessionManager(
            app=mcp._mcp_server,
            event_store=mcp._event_store,
            retry_interval=mcp._retry_interval,
            json_response=mcp.settings.json_response,
            stateless=mcp.settings.stateless_http,
            security_settings=mcp.settings.transport_security,
        )
    
    streamable_app = StreamableHTTPASGIApp(mcp._session_manager)
    
    routes = [
        Route("/", endpoint=streamable_app),
        Route("/mcp", endpoint=streamable_app),
        Route("/sse", endpoint=streamable_app),
    ]
    
    app = Starlette(
        debug=False,
        routes=routes,
        lifespan=lambda _: mcp._session_manager.run(),
    )
    
    logger.info(f"Starting MCP Server on HTTP (Streamable MCP on /, /mcp, /sse) at http://{host}:{port} ...")
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Enterprise Tech Support & Oracle ADB MCP Server")
    parser.add_argument("--transport", choices=["stdio", "sse", "streamable-http", "http"], default="streamable-http", help="Transport mode (default: streamable-http)")
    parser.add_argument("--host", default="0.0.0.0", help="Host for HTTP server")
    parser.add_argument("--port", type=int, default=8000, help="Port for HTTP server")
    args = parser.parse_args()

    if args.transport in ("sse", "streamable-http", "http"):
        run_http_server(host=args.host, port=args.port)
    else:
        logger.info("Starting MCP Server with stdio transport...")
        mcp.run(transport="stdio")

