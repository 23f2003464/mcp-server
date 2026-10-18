import hashlib
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

EMAIL = "23f2003464@ds.study.iitm.ac.in".strip().lower()

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
                   allow_headers=["*"], expose_headers=["*"])

TOOL = {
    "name": "solve_challenge",
    "description": "Returns the exam answer derived from the X-Exam-Challenge request header.",
    "inputSchema": {"type": "object", "properties": {}},
}


def answer(challenge: str) -> str:
    return hashlib.sha256(f"{challenge}:{EMAIL}".encode()).hexdigest()[:16]


def handle(msg: dict, request: Request):
    method = msg.get("method")
    mid = msg.get("id")
    if mid is None:  # notification
        return None
    if method == "initialize":
        ver = (msg.get("params") or {}).get("protocolVersion", "2025-03-26")
        result = {
            "protocolVersion": ver,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "exam-mcp", "version": "1.0.0"},
        }
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": [TOOL]}
    elif method == "tools/call":
        name = (msg.get("params") or {}).get("name")
        if name != "solve_challenge":
            return {"jsonrpc": "2.0", "id": mid,
                    "error": {"code": -32602, "message": f"Unknown tool: {name}"}}
        challenge = (request.headers.get("x-exam-challenge") or "").strip()
        result = {"content": [{"type": "text", "text": answer(challenge)}], "isError": False}
    else:
        return {"jsonrpc": "2.0", "id": mid,
                "error": {"code": -32601, "message": f"Method not found: {method}"}}
    return {"jsonrpc": "2.0", "id": mid, "result": result}


@app.post("/mcp")
@app.post("/")
async def mcp(request: Request):
    try:
        body = await request.json()
    except Exception:
        return Response(
            content='{"jsonrpc":"2.0","id":null,"error":{"code":-32700,"message":"Parse error"}}',
            media_type="application/json", status_code=400)
    if isinstance(body, list):
        outs = [r for r in (handle(m, request) for m in body) if r is not None]
        if not outs:
            return Response(status_code=202)
        return outs
    out = handle(body, request)
    if out is None:
        return Response(status_code=202)
    return out


@app.get("/mcp")
@app.get("/")
async def info():
    return {"status": "ok", "mcp_endpoint": "POST /mcp"}
