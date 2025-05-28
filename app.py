import os
import re
import time
import glob
import base64
from PIL import Image
import pandas as pd
import ast
import streamlit as st
from openai import OpenAI

# Function to load files
def load_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

# Function to load images
def load_image(path):
    return Image.open(path)

# Function to encode images so we can send them to the model
def encode_image(image_path):
  with open(image_path, "rb") as image_file:
    return base64.b64encode(image_file.read()).decode('utf-8')

# Function to load dataframe's edag topics information (and save it in cache)
@st.cache_data
def load_edag_topics(path='data/enade_data.csv'):
    df = pd.read_csv(path, converters={'test_content_edag': ast.literal_eval})
    return {row['year']: row['test_content_edag'] for _, row in df.iterrows()}

# Function to validate question format
def validate_question_format(text, fmt):
    # Question starts with “PERGUNTA:” and contains “JUSTIFICATIVA:”?
    if not text.startswith("PERGUNTA:") or "JUSTIFICATIVA:" not in text:
        return False

    # Trying to get rid of questions on the introction text without filtering too much for the model's creativity
    try:
        intro = text.split("PERGUNTA:\n",1)[1].split("\n\n",1)[0]
        if "?" == intro[-1]:
            return False
    except:
        return False

    # Testing regex for question structure
    if fmt == 'resposta_unica':
        pattern = r"""
            ^PERGUNTA:\n
            .+\n\n
            .+\n\n
            .+\n\n
            \(A\)\s.+\n
            \(B\)\s.+\n
            \(C\)\s.+\n
            \(D\)\s.+\n
            \(E\)\s.+\n\n
            JUSTIFICATIVA:\n
            \(A\)\s.+\n
            \(B\)\s.+\n
            \(C\)\s.+\n
            \(D\)\s.+\n
            \(E\)\s.+$
        """

    elif fmt == 'resposta_multipla':
        pattern = r"""
            ^PERGUNTA:\n
            .+\n\n
            .+\n\n
            I\.\s+.+\n
            II\.\s+.+\n
            III\.\s+.+\n
            IV\.\s+.+\n\n
            É correto apenas o que se afirma em:\n\n
            \(A\)\s+I\n
            \(B\)\s+II e IV\n
            \(C\)\s+III e IV\n
            \(D\)\s+I, II e III\n
            \(E\)\s+I, II, III e IV\n\n
            JUSTIFICATIVA:\n
            I\.\s+.+\n
            II\.\s+.+\n
            III\.\s+.+\n
            IV\.\s+.+s$
        """

    elif fmt == 'discursiva':
        pattern = r"""
            ^PERGUNTA:\n
            .+\n\n
            .+\n\n
            .+\n\n
            JUSTIFICATIVA:\n
            .+$
        """

    elif fmt == 'assercao_razao':
        pattern = r"""
            ^PERGUNTA:\n
            .+\n\n
            .+\n\n
            Nesse contexto, avalie as asserções a seguir e a relação proposta entre elas:\n\n
            I\.\s+.+\n\n
            \*\*PORQUE\*\*\n\n
            II\.\s+.+\n\n
            À respeito dessas asserções, assinale a opção correta:\n\n
            \(A\)\s+As asserções I e II são proposições verdadeiras, e a II é uma justificativa correta da I\.\n
            \(B\)\s+As asserções I e II são proposições verdadeiras, mas a II não é uma justificativa correta da I\.\n
            \(C\)\s+A asserção I é uma proposição verdadeira, e a II é uma proposição falsa\.\n
            \(D\)\s+A asserção I é uma proposição falsa, e a II é uma proposição verdadeira\.\n
            \(E\)\s+As asserções I e II são proposições falsas\.\n\n
            JUSTIFICATIVA:\n
            I\.\s+.+\n
            II\.\s+.+\n\n
            .+$
        """
    
    return bool(re.match(pattern, text, re.DOTALL | re.VERBOSE))

# Initializing API client
groq_key = load_file('data/keys/groq').strip()
# groq_key = st.secrets["groq"]["key"]
os.environ['OPENAI_API_KEY'] = groq_key
client = OpenAI(
    base_url='https://api.groq.com/openai/v1',
    api_key=os.environ['OPENAI_API_KEY'],
)

# Page configuration
st.set_page_config(page_title='Gerador de Questões EDAG', layout='wide', initial_sidebar_state='collapsed')

# Addition to the title
st.markdown(
    """
    <div style="text-align: center;">
        <h1>Gerador de Questões EDAG <span style="font-size: xx-small;">by Luis Zerkowski</span></h1>
    </div>
    """,
    unsafe_allow_html=True
)

# Custom CSS for streamlit
st.markdown(
    """
    <style>
        /* Centering the main title */
        h1 { text-align: center; }

        /* Bigger labels for selectors */
        div[data-testid="stMarkdownContainer"]{
            font-size: 24px !important;
        }

        /* Reducing spacing between labels and text areas */
        div[data-testid="stSubHeader"] > label {
            margin-bottom: 0px !important;
        }

        /* Increasing textbox area */
        div[data-testid="stTextInputRootElement"]{
            height: 8.5em !important;
        }

        /* Centralizing columns */
        div[data-testid="stColumn"].st-emotion-cache-vv2psj{
            display: flex !important;
            justify-content: center !important;
            align-items: center !important;
        }

    </style>
    """,
    unsafe_allow_html=True
)

# State variable later used for card (question) selection
if 'selected_question' not in st.session_state:
    st.session_state.selected_question = None

# Hard coded list of content from CIMATEC's perspective
edag_content_list = ['programação e engenharia de software', 'robótica', 'eletrônica e elétrica', 'arquitetura de computadores e sistemas operacionais', 'inteligência artificial', 'sistemas distribuídos e programação paralela', 'redes, cloud e segurança', 'sistemas embarcados e iot', 'sistemas digitais e sinais', 'outros']

# Loading topics
edag_topics_by_year = load_edag_topics()

# Topic selector
topics_display = st.multiselect('Escolha um ou mais tópicos', [t.title() for t in edag_content_list], placeholder='Todos os tópicos')
topics = [t.lower() for t in topics_display]

# Creating selectors on top
cols = st.columns([1, 1, 1])

# Format mapping
format_files = glob.glob('data/edag_question_formats/*.txt')
format_names = [os.path.basename(f) for f in format_files]
display_formats = [os.path.splitext(name)[0].replace('_', ' ').title() for name in format_names]
fmt_map = dict(zip(display_formats, format_names))

with cols[0]:
    chosen_fmt = st.selectbox('Formato da Nova Questão', display_formats)
    fmt_filter = fmt_map[chosen_fmt]

# Year selector
years = sorted([int(prova.split('_')[-1]) for prova in glob.glob('data/visual_approach/prova_*')])
with cols[1]:
    year_filter = st.selectbox('Ano da Prova', ['Todos'] + [str(y) for y in years])

# Type mapping
raw_types = sorted({questao.split('_')[0] for questao in os.listdir(f'data/visual_approach/prova_{2023}')})
type_map = {'closed': 'Fechada', 'open': 'Discursiva'}
inv_type_map = {v: k for k, v in type_map.items()}
display_types = ['Todos'] + [type_map.get(t, t.title()) for t in raw_types]

# Question type selector
with cols[2]:
    type_filter = st.selectbox('Tipo de Questão', display_types)

# Text box for additional instructions and button to generate question
gen_col, upload_col, btn_col = st.columns([3, 1, 1])
user_prompt = gen_col.text_input('Instruções Adicionais (opcional)')
uploaded_graphic = upload_col.file_uploader('Suporte Gráfico (opcional)', type=['png'])
generate_clicked = btn_col.button('Gerar Questão')

# Placeholder for new question
new_q_placeholder = st.empty()

# Question generation logic
if generate_clicked:
    # Building up pipeline message
    msgs = []
    sys_content = (
        "Sua função é gerar markdown de uma nova questão de prova dentro dos [TÓPICOS] fornecidos e seguindo exatamente o [FORMATO DE SAÍDA] fornecido através do preenchimento dos trechos marcados por '<>'. Não responda ao conteúdo da questão original. Não adicione comentários, cabeçalhos, explicações, saudações ou qualquer texto extra. Retorne apenas o texto da nova questão, nada mais. Caso haja uma imagem [QUESTÃO BASE], siga seu tema para gerar a nova questão. Caso haja uma image [ANEXO GRÁFICO], use-a como suporte gráfico na geração da nova questão. Caso haja [INSTRUÇÕES ADICIONAIS], siga exatamente o que for pedido."
    )
    msgs.append({'role':'system','content':sys_content})

    # Adding user content
    content_list = []
    
    # Adjust for selected question
    if st.session_state.selected_question:
        path = st.session_state.selected_question['path']
        img_b64 = encode_image(path)
        content_list.append({'type': 'text', 'text': '\n\n[QUESTÃO BASE]\n'})
        content_list.append({'type':'image_url','image_url':{'url':f"data:image/png;base64,{img_b64}"}})
    
    # Adjut for graphic support
    if uploaded_graphic is not None:
        data = uploaded_graphic.read()
        graphic_b64 = encode_image(data)
        content_list.append({'type': 'text', 'text': '\n\n[ANEXO GRÁFICO]\n'})
        content_list.append({'type':'image_url','image_url':{'url':f"data:image/png;base64,{graphic_b64}"}})
    
    # Basic text with topics and format
    if len(topics) != 0:
        text_block = f"\n\n[TÓPICOS]\n{topics}\n\n[FORMATO DE SAÍDA]\n{load_file(f'data/edag_question_formats/{fmt_filter}') }"
    else:
        text_block = f"\n\n[TÓPICOS]\n{edag_content_list}\n\n[FORMATO DE SAÍDA]\n{load_file(f'data/edag_question_formats/{fmt_filter}') }"

    # Adjust for user instructions
    if user_prompt:
        text_block += f"\n\n[INSTRUÇÕES ADICIONAIS]\n{user_prompt}"
    
    msgs.append({'role':'user','content':content_list + [{'type':'text','text':text_block}]})

    # Trying to generate question
    max_attempts = 5
    new_q = None
    for attempt in range(max_attempts):
        # API call
        resp = client.chat.completions.create(
            # model="meta-llama/llama-3.3-70b-versatile",
            # model='meta-llama/llama-4-scout-17b-16e-instruct',
            model='meta-llama/llama-4-maverick-17b-128e-instruct',
            messages=msgs,
            temperature=1.2,
            max_tokens=2048
        )

        # Validating question
        candidate = resp.choices[0].message.content.strip()
        if validate_question_format(candidate, fmt_filter.split('.')[0]):
            new_q = candidate
            break

        # If failed, changing message to try again
        msgs.append({
            'role':'user',
            'content': ("O formato da questão não seguiu exatamente o template. Por favor, gere novamente exatamente no formato fornecido.")
        })
        time.sleep(2)

    if new_q:
        new_q_placeholder.markdown(new_q, unsafe_allow_html=True)
    else:
        st.error("Não consegui gerar a questão no formato correto após várias tentativas. Pode tentar novamente?")

# Expanded question view logic
if st.session_state.selected_question:
    sq = st.session_state.selected_question

    if st.button('Voltar'):
        st.session_state.selected_question = None
        st.rerun()

    st.image(sq['url'], caption=f"{type_map.get(sq['type'], sq['type'].title())} {sq['number']:02d}", output_format='PNG')

# Card grid view
else:
    # Getting questions
    all_qs = []
    for y in years:
        year_topics = edag_topics_by_year.get(y, {})
        for fname in sorted(os.listdir(f'data/visual_approach/prova_{y}')):
            qtype_raw, _, num_ext = fname.partition('_question_')
            num = int(num_ext.split('.')[0])

            # Applying filters
            qkey = f"{qtype_raw}_question_{num:02d}"
            qtopics = year_topics.get(qkey, [])
            if topics and not set(qtopics).intersection(topics):
                continue

            if year_filter != 'Todos' and str(y) != year_filter:
                continue
            
            disp_type = type_map.get(qtype_raw, qtype_raw.title())
            if type_filter != 'Todos' and disp_type != type_filter:
                continue
            
            # Storing question
            path = f'data/visual_approach/prova_{y}/{fname}'
            all_qs.append({'year': y, 'type': qtype_raw, 'number': num, 'path': path, 'url': 'https://raw.githubusercontent.com/Luizerko/enade_to_edag/main/' + path})

    # Grouping questions
    grouped = {}
    for q in all_qs:
        try:
            grouped[q['year']].append(q)
        except:
            grouped[q['year']] = [q]

    # Exhibiting qiestions in grid fashion
    for y in sorted(grouped.keys(), reverse=True):
        cols = st.columns([1, 20])
        with cols[0]:
            st.markdown("")
            st.markdown(f"**{y}**")
        with cols[1]:
            st.markdown(f"---")
        

        qs = grouped[y]
        for i in range(0, len(qs), 4):
            row = qs[i:i+4]
            cols = st.columns(len(row))
            for col, q in zip(cols, row):
                with col:
                    st.image(q['url'], output_format='PNG')
                    label = f"Questão {type_map.get(q['type'], q['type'].title())} {q['number']:02d}"
                    if st.button(label, key=f"select_{y}_{q['type']}_{q['number']}"):
                        st.session_state.selected_question = q
                        st.rerun()