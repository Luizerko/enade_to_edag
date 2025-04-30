import os
import glob
import streamlit as st
from openai import OpenAI

# Function to load files
def load_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

# Initializing API client
groq_key = load_file('data/keys/groq').strip()
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
years = sorted([int(prova.split('_')[-1]) for prova in glob.glob('data/prova_*')])
with cols[0]:
    year = st.selectbox('Ano da Prova', years)

# Type mapping
raw_types = sorted({questao.split('_')[0] for questao in os.listdir(f'data/prova_{2014}/clean')})
type_map = {'closed': 'Fechada', 'open': 'Discursiva'}
inv_type_map = {v: k for k, v in type_map.items()}
display_types = [type_map.get(t, t.title()) for t in raw_types]

# Question type selector
with cols[1]:
    qtype = st.selectbox('Tipo de Questão', display_types)

# Question number selector
questoes = sorted(os.listdir(f'data/prova_{year}/clean'))
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
original_path = f'data/prova_{year}/clean/{inv_type_map[qtype]}_question_{number:02d}.txt'
question_format = load_file(f'data/edag_question_formats/{fmt_file}')
original_question = load_file(original_path)

# Displaying original question and creating placeholder for new question
left, right = st.columns(2)
with left:
    st.subheader('Questão Original')
    st.text_area('', original_question, height=300)
with right:
    st.subheader('Nova Questão Gerada')
    new_q_placeholder = st.empty()
    new_q_placeholder.text_area('', '', height=300)

# Generation button
if st.button('Gerar Nova Questão'):
    response = client.chat.completions.create(
        #model="meta-llama/llama-3.3-70b-versatile",
        model='meta-llama/llama-4-scout-17b-16e-instruct',
        messages=[
            {
                'role': 'system',
                'content': "Você é um assistente cuja única função é gerar uma nova versão de uma questão do ENADE exatamente no formato de saída fornecido. Não responda ao conteúdo da questão original. Não adicione comentários, cabeçalhos, explicações, saudações ou qualquer texto extra (como “Aqui está” ou “Nova questão:”). Mantenha estritamente a estrutura, numeração, pontuação e estilo do formato de saída. Retorne apenas o texto da nova questão, nada mais.",
            },
            {
                'role': 'user',
                'content': f"""[QUESTÃO ORIGINAL]\n{original_question}\n\n[FORMATO DE SAÍDA]\n{question_format}""",
            },
        ],
        temperature=0.3,
        max_tokens=1024,
    )
    new_q = response.choices[0].message.content.strip()

    # Updating placeholder with actual new question
    new_q_placeholder.text_area('', new_q, height=300)