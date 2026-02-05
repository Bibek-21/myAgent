import json

import requests
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI()

tools = [
    {
        "type": "function",
        "function": {
            "name": "geocode",
            "description": "Convert a place name to latitude and longitude.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City, region, or country name.",
                    }
                },
                "required": ["location"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather for given latitude and longitude.",
            "parameters": {
                "type": "object",
                "properties": {
                    "latitude": {"type": "number"},
                    "longitude": {"type": "number"},
                },
                "required": ["latitude", "longitude"],
                "additionalProperties": False,
            },
        },
    },
]


def geocode(location: str) -> dict:
    response = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": location, "count": 1, "language": "en", "format": "json"},
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()
    results = data.get("results") or []
    if not results:
        return {"error": f"No coordinates found for '{location}'."}
    hit = results[0]
    return {
        "latitude": hit["latitude"],
        "longitude": hit["longitude"],
        "name": hit.get("name"),
        "country": hit.get("country"),
    }


def get_weather(latitude: float, longitude: float) -> dict:
    response = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,wind_speed_10m",
        },
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()
    return {
        "latitude": latitude,
        "longitude": longitude,
        "current": data.get("current", {}),
    }


def call_tool(name: str, args: dict) -> dict:
    if name == "geocode":
        return geocode(**args)
    if name == "get_weather":
        return get_weather(**args)
    raise ValueError(f"Unknown tool: {name}")


# prompt = input("Enter your prompt: ")
messages = [
    {
        "role": "system",
        "content": (
            "You are a helpful weather assistant. "
            "If the user gives a place name, call geocode to get coordinates. "
            "Then call get_weather with latitude and longitude. "
            "In your final reply, include latitude, longitude, and temperature_2m."
        ),
    },
    {"role": "user", "content": "what is the weather like in kathmandu?"},
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
        result = call_tool(name, args)
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
