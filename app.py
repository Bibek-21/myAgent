import os, json
from typing import Any, Dict, List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = FastAPI()

# -------------------------
# Example "tool" functions
# Replace with your DB/API
# -------------------------
def get_revenue_by_month(year: int) -> List[Dict[str, Any]]:
    return [
        {"month": "Jan", "revenue": 30, "growth": 5},
        {"month": "Feb", "revenue": 45, "growth": 8},
    ]

def make_chart_metadata(year: int) -> Dict[str, Any]:
    data = get_revenue_by_month(year)
    return {
        "actions": [
            {"id": "copy", "code": "copy", "label": "Copy"},
            {"id": "run", "code": "run", "label": "Run"},
            {"id": "explain", "code": "explain", "label": "Explain"},
            {"id": "refactor", "code": "refactor", "label": "Refactor"},
        ],
        "data": {
            "chartType": "bar",
            "data": data,
            "xKey": "month",
            "series": [
                {"key": "revenue", "type": "bar", "name": "Revenue", "color": "#faad14"},
                {"key": "growth", "type": "line", "name": "Growth", "color": "#722ed1"},
            ],
        },
    }

async def ws_send(ws: WebSocket, obj: Dict[str, Any]):
    # send each JSON object as its own WS frame (your frontend parser loves this)
    await ws.send_text(json.dumps(obj, ensure_ascii=False))

@app.websocket("/ws")
async def ws_chat(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            req = await ws.receive_json()

            messages = req.get("messages", [])
            ui = req.get("ui", {}) or {}
            want_chart = bool(ui.get("wantChart", False))
            year = int(ui.get("year", 2026))

            text_id = req.get("textId", "t1")

            # 1) stream-start (optional for your frontend, but good to keep)
            await ws_send(ws, {"type": "stream-start", "warnings": []})

            # 2) text-start (optional)
            await ws_send(ws, {"type": "text-start", "id": text_id})

            # Add instructions: the model can output markdown tables/code blocks
            system = {
                "role": "system",
                "content": (
                    "You are an admin assistant for our internal dashboard.\n"
                    "Answer in Markdown.\n"
                    "Use fenced code blocks for code.\n"
                    "Use Markdown tables for tabular data.\n"
                    "If a chart is requested, describe it briefly in text."
                )
            }

            # (Optional) Preload tool data into context
            # So the model’s text is consistent with the chart
            tool_context = []
            if want_chart:
                tool_context.append({
                    "role": "system",
                    "content": f"Revenue dataset for {year} (JSON): {json.dumps(get_revenue_by_month(year))}"
                })

            # 3) Stream tokens from OpenAI
            stream = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[system] + messages + tool_context,
                stream=True,
            )

            

            # 4) Send metadata (chart/table/etc)
            if want_chart:
                await ws_send(ws, {"type": "metadata", "metadata": make_chart_metadata(year)})

            # 5) text-end + finish (optional but good)
            await ws_send(ws, {"type": "text-end", "id": text_id})
            await ws_send(ws, {
                "type": "finish",
                "finishReason": "stop",
                "usage": {"inputTokens": 0, "outputTokens": 0, "totalTokens": 0}
            })

    except WebSocketDisconnect:
        return
