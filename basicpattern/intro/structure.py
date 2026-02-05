# pydantic library for structured outputs
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel
load_dotenv()
client = OpenAI()


class CalendarEvent(BaseModel):
    name:str
    data:str
    participant:list[str]
    
prompt = input("Enter your prompt: ")
completion = client.chat.completions.parse(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": "You're a helpful assistant."},
        {
            "role": "user",
            "content": prompt
        },
    ],
    response_format=CalendarEvent
)
response = completion.choices[0].message.content
print(response)
