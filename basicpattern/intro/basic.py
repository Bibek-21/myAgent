from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI()

prompt = input("Enter your prompt: ")
completion = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": "You're a helpful assistant."},
        {
            "role": "user",
            "content": prompt
        },
    ],
)
response = completion.choices[0].message.content
print(response)
