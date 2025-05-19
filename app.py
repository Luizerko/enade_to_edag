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
def load_image(path):
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
        font-size: 20px !important;
    }

    /* Reducing spacing between labels and text areas */
    div[data-testid="stSubHeader"] > label {
        margin-bottom: 0px !important;
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

# Topic selector
topics = st.multiselect('Escolha um ou mais tópicos', edag_content_list)

if topics:

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
            "Sua função é gerar markdown de uma nova questão de prova baseada em [TÓPICOS] e seguindo exatamente no [FORMATO DE SAÍDA] fornecido. Não responda ao conteúdo da questão original. Não adicione comentários, cabeçalhos, explicações, saudações ou qualquer texto extra. Retorne apenas o texto da nova questão, nada mais. Caso haja uma imagem, gere a nova questão no mesmo tema da questão base da figura. Caso haja uma segunda imagem, use a figura fornecida como suporte gráfico na geração da nova questão. Caso haja [INSTRUÇÕES ADICIONAIS], siga exatamente o que for pedido."
        )
        msgs.append({'role':'system','content':sys_content})

        # Adding user content
        content_list = []
        
        # Adjust for selected question
        if st.session_state.selected_question:
            path = st.session_state.selected_question['path']
            img_b64 = encode_image(path)
            content_list.append({'type':'image_url','image_url':{'url':f"data:image/png;base64,{img_b64}"}})
        
        # Adjut for graphic support
        if uploaded_graphic is not None:
            data = uploaded_graphic.read()
            graphic_b64 = encode_image(data)
            content_list.append({'type':'image_url','image_url':{'url':f"data:image/png;base64,{graphic_b64}"}})
        
        # Basic text with topics and format
        text_block = f"[TÓPICOS]\n{topics}\n[FORMATO DE SAÍDA]\n{load_file(f'data/edag_question_formats/{st.session_state.chosen_fmt}') }"

        # Adjust for user instructions
        if user_prompt:
            text_block += f"\n[INSTRUÇÕES ADICIONAIS]\n{user_prompt}"
        
        msgs.append({'role':'user','content':content_list + [{'type':'text','text':text_block}]})

        # API call
        resp = client.chat.completions.create(
            # model="meta-llama/llama-3.3-70b-versatile",
            # model='meta-llama/llama-4-scout-17b-16e-instruct',
            model='meta-llama/llama-4-maverick-17b-128e-instruct',
            messages=msgs,
            temperature=1,
            max_tokens=2048
        )
        new_q = resp.choices[0].message.content.strip()
        new_q_placeholder.markdown(new_q, unsafe_allow_html=True)

    # Expanded question view logic
    if st.session_state.selected_question:
        sq = st.session_state.selected_question

        if st.button('Voltar'):
            st.session_state.selected_question = None
            st.experimental_rerun()

        img = load_image(sq['path'])
        st.image(img, caption=f"{type_map.get(sq['type'], sq['type'].title())} {sq['number']:02d}", use_container_width=True, output_format='PNG')

    # Card grid view
    else:
        # Getting questions
        all_qs = []
        for y in years:
            for fname in sorted(os.listdir(f'data/visual_approach/prova_{y}')):
                qtype_raw, _, num_ext = fname.partition('_question_')
                num = int(num_ext.split('.')[0])

                # Applying filters
                if year_filter != 'Todos' and str(y) != year_filter:
                    continue
                
                disp_type = type_map.get(qtype_raw, qtype_raw.title())
                if type_filter != 'Todos' and disp_type != type_filter:
                    continue
                
                # Storing question
                path = f'data/visual_approach/prova_{y}/{fname}'
                all_qs.append({'year': y, 'type': qtype_raw, 'number': num, 'path': path})

        # Grouping questions
        grouped = {}
        for q in all_qs:
            try:
                grouped[q['year']].append(q)
            except:
                grouped[q['year']] = [q]

        # Exhibiting qiestions in grid fashion
        for y in sorted(grouped.keys(), reverse=True):
            cols = st.columns([1, 10])
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
                        # thumb = load_image(q['path'])
                        # st.image(thumb, use_container_width=True, output_format='PNG')
                        label = f"Questão {type_map.get(q['type'], q['type'].title())} {q['number']:02d}"
                        if st.button(label, key=f"select_{y}_{q['type']}_{q['number']}"):
                            st.session_state.selected_question = q
                            st.experimental_rerun()