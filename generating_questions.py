import os
from openai import OpenAI

# Function to load files
def load_file(file_path):
  with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()
  return content

# Connecting to groq
os.environ["OPENAI_API_KEY"] = load_file('data/keys/groq').strip()
client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.environ["OPENAI_API_KEY"],
)

# Reading question and format
test_year = 2023
question_type = 'closed'
test_question = 1
original_question = load_file(f'data/prova_{test_year}/{question_type}_question_{test_question:02d}.txt')

question_format = load_file('data/edag_question_formats/resposta_unica.txt')

# Making request
response = client.chat.completions.create(
    #model="meta-llama/llama-3.3-70b-versatile",
    model="meta-llama/llama-4-scout-17b-16e-instruct",
    messages=[
        {
            "role": "system",
            "content": "Você é um assistente especializado em escrever novas versões de questões do ENADE dado um formato de saída. Ignore ruídos ou elementos inválidos da questão original na escrita da nova questão.",
        },
        {
            "role": "user",
            "content": f"""[QUESTÃO ORIGINAL]
{original_question}

[FORMATO DE SAÍDA]
{question_format}"""
        },
    ],
    temperature=0.3,
    max_tokens=1024,
)

print('Nova Questão Gerada:\n')
print(response.choices[0].message.content)
print()