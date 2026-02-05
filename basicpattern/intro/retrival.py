import json
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI()

tools = [
    {
        "type": "function",
        "function": {
            "name": "search_kb",
            "description": "Find the most relevant answer from the knowledge base.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                },
                "required": ["question"],
                "additionalProperties": False,
            },
        },
    },
]


KB_PATH = Path(__file__).with_name("kb.json")


def load_kb() -> List[Dict[str, Any]]:
    with KB_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("records", [])


def score_match(query: str, text: str) -> int:
    query_tokens = {t for t in query.lower().split() if t}
    text_tokens = {t for t in text.lower().split() if t}
    return len(query_tokens & text_tokens)


def search_kb(question: str, records: List[Dict[str, Any]]) -> Dict[str, Any]:
    best = None
    best_score = -1
    for record in records:
        score = score_match(question, record.get("question", ""))
        if score > best_score:
            best = record
            best_score = score
    if not best or best_score == 0:
        return {
            "answer": "I couldn't find a direct match in the knowledge base.",
            "match_score": best_score,
        }
    return {
        "answer": best.get("answer", ""),
        "match_score": best_score,
        "matched_question": best.get("question", ""),
        "id": best.get("id"),
    }



def call_tool(name: str, args: dict, records: List[Dict[str, Any]]) -> dict:
    if name == "search_kb":
        return search_kb(records=records, **args)
    raise ValueError(f"Unknown tool: {name}")
      

def run() -> None:
    records = load_kb()
    prompt = input("Enter your prompt: ")
    messages = [
        {
            "role": "system",
            "content": (
                "You are a QA assistant. Use the search_kb tool to answer "
                "with the most relevant knowledge base entry."
            ),
        },
        {"role": "user", "content": prompt},
    ]

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        tools=tools,
    )

    while response.choices[0].message.tool_calls:
        messages.append(response.choices[0].message)
        for tool_call in response.choices[0].message.tool_calls:
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments or "{}")
            result = call_tool(name, args, records)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result),
                }
            )
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=tools,
        )

    print(response.choices[0].message.content)


if __name__ == "__main__":
    run()
