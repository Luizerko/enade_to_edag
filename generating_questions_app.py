import os
import glob
import base64
from PIL import Image
import streamlit as st
from openai import OpenAI

# Function to load files
def load_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

# Function to load images
def load_image(path: str) -> Image.Image:
    return Image.open(path)

# Function to encode images so we can send them to the model
def encode_image(image_path):
  with open(image_path, "rb") as image_file:
    return base64.b64encode(image_file.read()).decode('utf-8')

# Initializing API client
# groq_key = load_file('data/keys/groq').strip()
groq_key = st.secrets["groq"]["key"]
os.environ['OPENAI_API_KEY'] = groq_key
client = OpenAI(
    base_url='https://api.groq.com/openai/v1',
    api_key=os.environ['OPENAI_API_KEY'],
)

# Page configuration
st.set_page_config(page_title='Gerador de Questões EDAG', layout='wide', initial_sidebar_state='collapsed')
st.title('Gerador de Questões EDAG')

# Custom CSS for streamlit
st.markdown(
    """
    <style>
    /* Centering the main title */
    h1 { text-align: center; }

    /* Reducing spacing between labels and text areas */
    div[data-testid="stSubHeader"] > label {
        margin-bottom: 0px !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)


# Creating selectors on top
cols = st.columns([1, 1, 1, 1])

# Year selector
years = sorted([int(prova.split('_')[-1]) for prova in glob.glob('data/visual_approach/prova_*')])
with cols[0]:
    year = st.selectbox('Ano da Prova', years)

# Type mapping
raw_types = sorted({questao.split('_')[0] for questao in os.listdir(f'data/visual_approach/prova_{2023}')})
type_map = {'closed': 'Fechada', 'open': 'Discursiva'}
inv_type_map = {v: k for k, v in type_map.items()}
display_types = [type_map.get(t, t.title()) for t in raw_types]

# Question type selector
with cols[1]:
    qtype = st.selectbox('Tipo de Questão', display_types)

# Question number selector
questoes = sorted(os.listdir(f'data/visual_approach/prova_{year}'))
numbers = [int(questao.split('_')[-1].split('.')[0]) for questao in questoes if questao.startswith(inv_type_map[qtype])]
with cols[2]:
    number = st.selectbox('Número da Questão', numbers)

# Format mapping
format_files = glob.glob('data/edag_question_formats/*.txt')
format_names = [os.path.basename(f) for f in format_files]
display_formats = [os.path.splitext(name)[0].replace('_', ' ').title() for name in format_names]
fmt_map = dict(zip(display_formats, format_names))

# Format selector
with cols[3]:
    chosen_fmt = st.selectbox('Formato da Questão', display_formats)
    fmt_file = fmt_map[chosen_fmt]

# Loading content
original_path = f'data/visual_approach/prova_{year}/{inv_type_map[qtype]}_question_{number:02d}.png'
question_format = load_file(f'data/edag_question_formats/{fmt_file}')
original_question = load_image(original_path)

# Displaying original question and creating placeholder for new question
left, right = st.columns(2)
with left:
    st.subheader('Questão Original')
    img = load_image(original_path)
    st.image(img, use_column_width=True)
with right:
    st.subheader('Nova Questão Gerada')
    new_q_placeholder = st.empty()
    new_q_placeholder.text_area('', '', height=500)

# Generation button
if st.button('Gerar Nova Questão'):
    base64_image = encode_image(original_path)
    response = client.chat.completions.create(
        #model="meta-llama/llama-3.3-70b-versatile",
        # model='meta-llama/llama-4-scout-17b-16e-instruct',
        model='meta-llama/llama-4-maverick-17b-128e-instruct',
        messages=[
            {
                'role': 'system',
                'content': "Sua função é gerar uma nova questão de prova baseada numa imagem de uma questão original e seguindo exatamente no formato de saída fornecido. Não responda ao conteúdo da questão original. Não adicione comentários, cabeçalhos, explicações, saudações ou qualquer texto extra. Mantenha a estrutura, numeração, pontuação e estilo do [FORMATO DE SAÍDA]. Retorne apenas o texto da nova questão, nada mais.",
            },
            {
                'role': 'user',
                'content': [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64_image}",
                        },
                    },
                    {
                        'type': 'text',
                        'text': f"""[FORMATO DE SAÍDA]\n{question_format}""",
                    }
                ]
            },
        ],
        temperature=1,
        max_tokens=1024,
    )
    new_q = response.choices[0].message.content.strip()

    # Updating placeholder with actual new question
    new_q_placeholder.text_area('', new_q, height=500)