# signet-local

Reads only `http://127.0.0.1:8001/plates` on this PC. Does not print a full card number. There is no POST.

Check once:

`python mcp-server/server.py --once`

Cursor starts this file over stdin from `.cursor/mcp.json` under the name `signet-local`.
