# Read the local decline plate

`python custom-agent/agent.py`

Reads only `http://127.0.0.1:8001/plates` on this PC. Prints the five plate fields. If the body contains a full card number, it prints nothing and stops. There is no POST and no Render deploy.
