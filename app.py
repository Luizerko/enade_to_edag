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

# Function to encode images (file objects) coming from the user
def encode_image_fileobj(file_obj):
    file_obj.seek(0)
    return base64.b64encode(file_obj.read()).decode('utf-8')

# Function to load dataframe's edag topics information (and save it in cache)
@st.cache_data
def load_edag_topics(path='data/enade_data.csv'):
    df = pd.read_csv(path, converters={'test_content_edag': ast.literal_eval})
    return {row['year']: row['test_content_edag'] for _, row in df.iterrows()}

# Function to validate question format
def validate_question_format(text, fmt):
    # Question starts with “ENUNCIADO:” and contains “JUSTIFICATIVA:”?
    if not text.startswith("ENUNCIADO:") or "JUSTIFICATIVA:" not in text:
        return False

    # Trying to get rid of questions on the introction text without filtering too much for the model's creativity
    try:
        intro = text.split("ENUNCIADO:\n",1)[1].split("\n\n",1)[0]
        if "?" == intro[-1]:
            return False
    except:
        return False

    # Testing regex for question structure
    if fmt == 'resposta_unica':
        pattern = r"^ENUNCIADO:\n[^\n]+\n\n[^\n]+\n\n\(A\) [^\n]+\n\(B\) [^\n]+\n\(C\) [^\n]+\n\(D\) [^\n]+\n\(E\) [^\n]+\n\nJUSTIFICATIVA:\n\(A\) [^\n]+\n\(B\) [^\n]+\n\(C\) [^\n]+\n\(D\) [^\n]+\n\(E\) [^\n]+$"

    elif fmt == 'resposta_multipla':
        pattern = r"^ENUNCIADO:\n[^\n]+\n\nI\. [^\n]+\nII\. [^\n]+\nIII\. [^\n]+\nIV\. [^\n]+\n\nÉ correto apenas o que se afirma em:\n\n\(A\) I\n\(B\) II e IV\n\(C\) III e IV\n\(D\) I, II e III\n\(E\) I, II, III e IV\n\nJUSTIFICATIVA:\nI\. [^\n]+\nII\. [^\n]+\nIII\. [^\n]+\nIV\. [^\n]+\n\nPortanto a alternativa correta é [A,B,C,D,E]$"

    elif fmt == 'discursiva':
        pattern = r"^ENUNCIADO:\n[^\n]+\n\n[^\n]+\n\nJUSTIFICATIVA:\n[^\n]+$"

    elif fmt == 'assercao_razao':
        pattern = r"^ENUNCIADO:\n[^\n]+\n\nNesse contexto, avalie as asserções a seguir e a relação proposta entre elas:\n\nI\. [^\n]+\n\n\*\*PORQUE\*\*\n\nII\. [^\n]+\n\nÀ respeito dessas asserções, assinale a opção correta:\n\n\(A\) As asserções I e II são proposições verdadeiras, e a II é uma justificativa correta da I\.\n\(B\) As asserções I e II são proposições verdadeiras, mas a II não é uma justificativa correta da I\.\n\(C\) A asserção I é uma proposição verdadeira, e a II é uma proposição falsa\.\n\(D\) A asserção I é uma proposição falsa, e a II é uma proposição verdadeira\.\n\(E\) As asserções I e II são proposições falsas\.\n\nJUSTIFICATIVA:\nI\. [^\n]+\nII\. [^\n]+\n\n[^\n]+$"
    
    return bool(re.match(pattern, text, flags=0))

# Function modal with decorator to show new question
@st.dialog('Nova Questão Gerada')
def show_new_q():
    # Rendering question generation error
    if st.session_state.modal_error:
        st.error(st.session_state.modal_error)
        st.session_state.modal_error = None

    # Rendering generated question
    # st.text(st.session_state.modal_content)
    st.markdown(st.session_state.modal_content, unsafe_allow_html=True)

    # Close button inside the dialog
    if st.button("Close", key="close_modal"):
        st.session_state.show_modal = False
        st.rerun()

# Initializing API client
# key = load_file('data/keys/groq').strip()
key = st.secrets["groq"]["key"]
os.environ['OPENAI_API_KEY'] = key
client = OpenAI(
    base_url='https://api.groq.com/openai/v1',
    api_key=os.environ['OPENAI_API_KEY'],
)

# key = load_file('data/keys/maritaca').strip()
# key = st.secrets["maritaca"]["key"]
# os.environ['OPENAI_API_KEY'] = key
# client = OpenAI(
#     base_url='https://chat.maritaca.ai/api',
#     api_key=os.environ['OPENAI_API_KEY'],
# )

# key = load_file('data/keys/openai').strip()
# key = st.secrets["openai"]["key"]
# os.environ['OPENAI_API_KEY'] = key
# client = OpenAI(
#     base_url='https://api.groq.com/openai/v1',
#     api_key=os.environ['OPENAI_API_KEY'],
# )

# Page configuration
st.set_page_config(page_title='Gerador de Questões do EDAG', layout='wide', initial_sidebar_state='collapsed')

# Addition to the title
st.markdown(
    """
    <div style="text-align: center;">
        <h1>Gerador de Questões do EDAG <span style="font-size: xx-small;">by Luis Zerkowski</span></h1>
    </div>
    """,
    unsafe_allow_html=True
)

# Custom CSS for streamlit
st.markdown(
    """
    <style>
        /* Centering the main title */
        h1 {
            text-align: center;
        }

        /* Bigger labels for selectors */
        div[data-testid="stMarkdownContainer"] {
            font-size: 24px !important;
        }

        /* Reducing spacing between labels and text areas */
        div[data-testid="stSubHeader"] > label {
            margin-bottom: 0px !important;
        }

        /* Creating a bit more space between block in a horizontal block */
        div[data-testid="stHorizontalBlock"] {
            gap: 1.2rem !important;
        }

        /* Centralizing columns for button that generates questions */
        div[data-testid="stColumn"]:has(> div > div > div > div[data-testid="stButton"]) {
            display: flex !important;
            justify-content: center !important; 
            align-items: center !important;
        }

        /* Centralizing slider and making it smaller */
        div[data-baseweb="slider"] {
            padding-left: 1em !important;
            width: 90% !important;
        }

        /* Making buttons larger */
        button[data-testid="stBaseButton-secondary"] {
            height: 4em !important;
            width: 12em !important;
        }

        /* Centralizing drag and drop of files */
        section[data-testid="stFileUploaderDropzone"] {
            align-items: center !important;
        }

        div[data-testid="stFileUploaderDropzoneInstructions"] {
            margin-right: 0 !important;
        }    

        /* Centering provas antigas title */
        h2 {
            text-align: center;
            font-weight: bold !important;
            margin-top: 3em !important;
        }

        /* Making year separation bigger and centralized */
        .year-separation {
            font-size: 40px !important;
            line-height: 1.5em !important;
        }

        /* Centralizing grid buttons */
        div[data-testid="stButton"] {
            display: flex !important;
            justify-content: center !important;
        }

        /* Separating grid lines */
        div[data-testid="stHorizontalBlock"]:has(> div > div > div > div > div > div > div[data-testid="stImage"]) {
            margin-bottom: 3em !important;
            padding-bottom: 2em !important;
            border-bottom: 2px dashed #aaa !important;
        }

        /* Resizing images on grid */
        div[data-testid="stHorizontalBlock"] > div > div > div > div > div > div > div > div[data-testid="stImageContainer"] {
            height: 30em !important;
            width: 20em !important;
        }
        
        img {
            height: 100% !important;
            object-fit: contain !important;
        }

        /* Removing toolbar from images */
        div[data-testid="stElementToolbar"] {
            display: none !important;
        }
        
        /* Resizing selected image */
        div[data-testid="stElementContainer"] > div > div > div > div[data-testid="stImageContainer"] {
            height: 60em !important;
        }

        /* Centralizing selected image */
        div[data-testid="stFullScreenFrame"] {
            display: flex !important;
            justify-content: center !important;
        }

        /* Increasing legend size for selected image */
        div[data-testid="stCaptionContainer"] {
            font-size: x-large !important;
            colot: black !important
        }

        /* Changing size of modal for newly generated question */
        div[data-testid="stDialog"] > div > div {
            width: 100em !important;
        }

        /* Removing small 'x' from modal to better control enviroment variable */
        button[aria-label="Close"] {
            display: None !important
        }

    </style>
    """,
    unsafe_allow_html=True
)

# State variable later used for card (question) selection
if 'selected_question' not in st.session_state:
    st.session_state.selected_question = None

# State variable for new question modal
if 'show_modal' not in st.session_state:
    st.session_state.show_modal = False
if 'modal_content' not in st.session_state:
    st.session_state.modal_content = ""
if 'modal_error' not in st.session_state:
    st.session_state.modal_error = None

# Hard coded list of content from CIMATEC's perspective
edag_content_list = ['algoritmos e estrutura de dados', 'arquitetura de computadores', 'banco de dados', 'cibersegurança', 'ciência de dados', 'elétrica e eletrônica', 'engenharia de software', 'grafos', 'inteligência artificial', 'iot', 'lógica de programação', 'processamento de sinais', 'redes de computadores', 'robótica, automação e controle', 'sistemas digitais', 'sistemas distribuídos e programação paralela', 'sistemas embarcados', 'sistemas operacionais e compiladores', 'outros']

# Loading topics
edag_topics_by_year = load_edag_topics()

# Topic selector
topics_display = st.multiselect('Escolha um ou mais tópicos', [t.title() for t in edag_content_list], placeholder='Todos os tópicos', help='Seletor de tópicos para gerar uma nova questão: o modelo usará os tópicos marcados (ou todos, se nenhum for escolhido) para criar uma pergunta. No caso de visualização de provas antigas do ENADE, o seletor filtra as questões por tópico. Note que a geração de uma questão pode combinar vários tópicos selecionados, então se você precisa de uma pergunta focada em um único tópico, selecione apenas aquele tópico.')
topics = [t.lower() for t in topics_display]

# Text box for format selection, additional instructions and button to generate question
fmt_col, gen_col, upload_col, btn_col = st.columns([1, 2, 1, 1])

# Format mapping
format_files = glob.glob('data/edag_question_formats/*.txt')
format_names = [os.path.basename(f) for f in format_files]
display_formats = [os.path.splitext(name)[0].replace('_', ' ').title() for name in format_names]
fmt_map = dict(zip(display_formats, format_names))

chosen_fmt = fmt_col.selectbox('Formato da Nova Questão', display_formats, help='Seletor de formato da nova questão baseado nos direcionamentos de padrão do EDAG.')
fmt_filter = fmt_map[chosen_fmt]
difficulty = fmt_col.select_slider('Nível de Dificuldade', ['Fácil', 'Médio', 'Difícil'], help='Seletor do nível de dificuldade da nova questão a ser gerada. Por conta da complexidade e subjetividaded inata em determinar o nível de dificuldade de uma questão, atente-se ao fato de que esse slider não garante uma questão fácil ou difícil.')

user_prompt = gen_col.text_area('Instruções Adicionais (opcional)', height=155, help='Área de texto para prompts adicionais e pedidos específicos que o usuário possar ter ao modelo quando da geração de uma nova questão.')

uploaded_graphic = upload_col.file_uploader('Suporte Gráfico (opcional)', type=['png'], help='Opção de upload de imagem (em formato PNG) para que o modelo possa utilizar quando da geração de uma nova questão. Note que a imagem aqui fornecida será necessariamente adicionada à questão, não apenas utilizada como inspiração.')

generate_clicked = btn_col.button('Gerar Questão')

# Question generation logic
if generate_clicked:
    # Building up pipeline message
    msgs = []
    sys_content = (
        "Sua função é gerar uma nova questão de prova dentro dos [TÓPICOS] fornecidos, na [DIFICULDADE] fornecida e seguindo exatamente o [FORMATO DE SAÍDA] fornecido através do preenchimento dos trechos indicados por '<>'. Não responda ao conteúdo da questão original. Não adicione comentários, cabeçalhos, explicações, saudações ou qualquer texto extra. Retorne apenas o texto da nova questão, nada mais. Caso haja [INSTRUÇÕES ADICIONAIS], siga exatamente o que for pedido. Caso haja uma imagem [QUESTÃO BASE], siga como exmplo para gerar a nova questão. Caso haja uma imagem [ANEXO GRÁFICO], use como suporte gráfico na geração da nova questão."
    )
    msgs.append({'role':'system','content':sys_content})

    # Basic text with topics and format
    if len(topics) != 0:
        text_block = f"\n\n[TÓPICOS]\n{topics}\n\n[DIFICULDADE]\n{difficulty}\n\n[FORMATO DE SAÍDA]\n{load_file(f'data/edag_question_formats/{fmt_filter}') }"
    else:
        text_block = f"\n\n[TÓPICOS]\n{edag_content_list}\n\n[DIFICULDADE]\n{difficulty}\n\n[FORMATO DE SAÍDA]\n{load_file(f'data/edag_question_formats/{fmt_filter}') }"

    # Adjust for user instructions
    if user_prompt:
        text_block += f"\n\n[INSTRUÇÕES ADICIONAIS]\n{user_prompt}"
    
    # Adding user content
    content_list = []
    
    # Adjust for selected question
    if st.session_state.selected_question:
        path = st.session_state.selected_question['path']
        img_b64 = encode_image(path)
        content_list.append({'type': 'text', 'text': '\n\n[QUESTÃO BASE]\n'})
        # content_list.append({'type':'image_url','image_url':{'url': f"data:image/png;base64,{img_b64}"}})
        content_list.append({'type':'image_url','image_url':{'url': st.session_state.selected_question['url']}})
    
    # Adjut for graphic support
    if uploaded_graphic is not None:
        graphic_b64 = encode_image_fileobj(uploaded_graphic)
        content_list.append({'type': 'text', 'text': '\n\n[ANEXO GRÁFICO]\n'})
        content_list.append({'type':'image_url','image_url':{'url':f"data:image/png;base64,{graphic_b64}"}})
    
    # Creating message for groq models
    msgs.append({'role':'user','content':[{'type':'text','text':text_block}] + content_list})

    # "Flattening" content for Maritaca's API
    # flattened = text_block
    # for item in content_list:
    #     if item["type"] == "text":
    #         flattened += item["text"]
    #     
    #     elif item["type"] == "image_url":
    #         flattened += item["image_url"]["url"]

    # msgs.append({"role": "user", "content": flattened})

    # Trying to generate question
    max_attempts = 3
    new_q = None
    for attempt in range(max_attempts):
        # API call
        resp = client.chat.completions.create(
            # model="llama-3.3-70b-versatile",
            model='meta-llama/llama-4-maverick-17b-128e-instruct',
            # model='sabia-3.1',
            messages=msgs,
            temperature=0.8,
            max_tokens=4096
        )

        # Validating question
        candidate = resp.choices[0].message.content.strip()
        print(repr(candidate), fmt_filter.split('.')[0])
        if validate_question_format(candidate, fmt_filter.split('.')[0]):
            new_q = candidate.replace('\n', '  \n')
            break

        # If failed, changing message to try again
        if attempt == 0:
            msgs.append({
                'role':'user',
                'content': ("O formato da questão não seguiu exatamente o template. Por favor, gere novamente exatamente no formato fornecido.")
            })
        time.sleep(5)

    if new_q:
        # Adding Anexo Gráfico to question if it exists
        if uploaded_graphic is not None:
            new_q = new_q.replace('  \n  \n', f'  \n  \n![Anexo Gráfico](data:image/png;base64,{graphic_b64})  \n  \n', 1)

        st.session_state.show_modal = True
        st.session_state.modal_content = new_q
    else:
        candidate = candidate.replace('\n', '  \n')

        # Adding Anexo Gráfico to question if it exists
        if uploaded_graphic is not None:
            candidate = candidate.replace('  \n  \n', f"  \n  \n<img src='data:image/png;base64,{graphic_b64}'>  \n  \n", 1)

        st.session_state.show_modal = True
        st.session_state.modal_content = candidate
        st.session_state.modal_error = "Não consegui gerar a questão no formato correto após várias tentativas, mas aí está uma pergunta candidata!"

# Creating modal with new question
if st.session_state.show_modal:
    show_new_q()

# Type mapping
raw_types = sorted({questao.split('_')[0] for questao in os.listdir(f'data/visual_approach/prova_{2023}')})
type_map = {'closed': 'Fechada', 'open': 'Discursiva'}
inv_type_map = {v: k for k, v in type_map.items()}

# Expanded question view logic
if st.session_state.selected_question:
    st.markdown("")
    st.markdown('<h2>Questão Base Selecionada</h2>', unsafe_allow_html=True)
    st.markdown("")

    sq = st.session_state.selected_question

    if st.button('Voltar'):
            st.session_state.selected_question = None
            st.rerun()

    st.image(sq['url'], caption=f"Questão {type_map.get(sq['type'], sq['type'].title())} {sq['number']:02d}", output_format='PNG')

# Card grid view
else:
    st.markdown("")
    st.markdown('<h2>Questões de Provas Antigas do ENADE</h2>', unsafe_allow_html=True)
    st.markdown("")
    # st.markdown("", help="Seção com questões de provas antigas do ENADE. A ideia é permitir que uma questão seja selecionada para ser usada como base na geração de uma nova questão.")

    # Creating selectors on top
    cols = st.columns([1, 1])

    # Year selector
    years = sorted([int(prova.split('_')[-1]) for prova in glob.glob('data/visual_approach/prova_*')])
    with cols[0]:
        year_filter = st.selectbox('Ano da Prova', ['Todos'] + [str(y) for y in years], help='Filtro de seleção do(s) ano(s) de prova antiga a ser analisado. Note que o usuário também pode escolher analisar todos os anos de prova.')

    # Question type selector
    display_types = ['Todos'] + [type_map.get(t, t.title()) for t in raw_types]
    with cols[1]:
        type_filter = st.selectbox('Tipo de Questão', display_types, help='Filtro de seleção do(s) tipo(s) de questão a ser analisado. Note que o usuário também pode escolher analisar todos os tipos de questão.')

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
        cols = st.columns([1, 14])
        with cols[0]:
            st.markdown("")
            st.markdown(f"<b class='year-separation'>{y}</b>", unsafe_allow_html=True)
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