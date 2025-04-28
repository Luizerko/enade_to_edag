import time
import re
import os
import io

from playwright.sync_api import sync_playwright
import fitz
from bs4 import BeautifulSoup
import pandas as pd
import requests
from pdf2image import convert_from_bytes
import pytesseract

# Normalizing text for when we want to compare strings
def normalize(text):
    return text.strip().lower()

# Funciton to click and reject cookies
def reject_cookies(page):
    try:
        page.wait_for_selector("button:has-text('Rejeitar cookies')", timeout=5000)
        page.click("button:has-text('Rejeitar cookies')")
    except:
        print("Aba de cookies não apareceu?\n")

# Function to try and handle failing get requests
def safe_get(url, retries=5, backoff_factor=1.2):
    for i in range(retries):
        try:
            return requests.get(url, timeout=10)
        except Exception as e:
            print(f"Falha no request {i+1} de {retries}: {e}\n")
            time.sleep(backoff_factor*(2**i))

# Function to figure out if a text is garbage we did not manage to decode or proper text
def garbage_text(text, threshold=0.5):
    # Removing spaces and punctuation
    cleaned_text = re.sub(r'[\W_]+', '', text)
    
    # Check if the text is either empty or only symbols (garbage)
    if not cleaned_text:
        return True

    # Counting latin alphabet characters
    latin_chars = re.findall(r'[A-Za-zÀ-ÿ]', cleaned_text)
    ratio = len(latin_chars)/len(cleaned_text)

    return ratio<threshold

# Parsing PDF to extract ENADE theoretical content
def parse_pdf_theoretical(url, course, year):
    try:
        # Getting PDF
        response = safe_get(url)
        pdf_stream = io.BytesIO(response.content)
        doc = fitz.open(stream=pdf_stream, filetype="pdf")

        # Finding all lines of the PDF and accumulating contents for Art. 6 or 7
        art_string = 'art. 6' if year > 2017 else 'art. 7'
        next_art_string = 'art. 7' if year > 2017 else 'art. 8'

        # Start looking for content only after matching our course (to parse even in Diários Oficiais)
        seen_course = False

        is_cont_art = False
        content_list = []
        for page in doc:
            # Fixing potential PDF broken lines (e.g. I-\nAdministração e Economia)
            raw_lines = page.get_text().split('\n')
            lines = []
            i = 0
            while i < len(raw_lines):
                current_line = raw_lines[i].strip()

                # Checking if line looks like "I-", "II -", etc. but doesn't have real content
                if re.match(r"^(I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII|XIII|XIV|XV|XVI|XVII|XVIII|XIX|XX|XXI)[\s\-–:.]*$", current_line, re.IGNORECASE):
                    if i+1 < len(raw_lines):
                        current_line += " " + raw_lines[i+1].strip()
                        i += 1

                lines.append(current_line)
                i += 1

            for line in lines:
                line = normalize(line.strip())
                
                # Wait until the course appears before parsing anything else
                if not seen_course:
                    if course in line:
                        seen_course = True
                    continue

                # Testing Art 6 or 7 start
                if not is_cont_art and line.startswith(art_string):
                    is_cont_art = True

                # Getting Art 6 or 7 content
                elif is_cont_art:
                    # Stop accumulating content
                    if line.startswith(next_art_string):
                        break

                    match = re.match(r"^(I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII|XIII|XIV|XV|XVI|XVII|XVIII|XIX|XX|XXI)[\s\-–:.]+(.+)", line, re.IGNORECASE)
                    if match:
                        content = match.group(2).strip()[:-1]
                        content_list.append(content)

        content_list.append('outros')
        return content_list

    except Exception as e:
        print(f"Não foi possível parsear o PDF {url}: {e}\n")
        return []

# Parsing HTML to extract ENADE theoretical content
def parse_html_theoretical(url, course, year):
    try:
        # Getting HTML
        response = safe_get(url)
        soup = BeautifulSoup(response.content, "html.parser")

        # Finding all lines of the HTML and accumulating contents for Art. 6 or 7
        paragraphs = soup.find_all("p", class_="dou-paragraph")

        art_string = 'art. 6' if year > 2017 else 'art. 7'
        next_art_string = 'art. 7' if year > 2017 else 'art. 8'

        # Start looking for content only after matching our course (to parse even in Diários Oficiais)
        seen_course = False

        is_cont_art = False
        content_list = []
        for p in paragraphs:
            text = normalize(p.get_text(strip=True))

            # Wait until the course appears before parsing anything else
            if not seen_course:
                if course in text:
                    seen_course = True
                continue

            # Testing Art. 6 or 7 start
            if not is_cont_art and text.startswith(art_string):
                is_cont_art = True

            # Getting Art. 6 or 7 content
            elif is_cont_art:
                # Stop acumulating content
                if text.startswith(next_art_string):
                    break

                match = re.match(r"^(I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII|XIII|XIV|XV|XVI|XVII|XVIII|XIX|XX|XXI)[\s\-–:.]+(.+)", text, re.IGNORECASE)
                if match:
                    content = match.group(2).strip()[:-1]
                    content_list.append(content)

        content_list.append('outros')
        return content_list

    except Exception as e:
        print(f"Não foi possível parsear o HTML {url}: {e}\n")
        return []

# Parsing PDF to extract ENADE test content
def parse_pdf_test(url, year):
    try:
        # Getting PDF
        response = safe_get(url)
        pdf_stream = io.BytesIO(response.content)
        doc = fitz.open(stream=pdf_stream, filetype="pdf")

        # Creating folder to store individual questions
        output_folder = f"data/prova_{year}"
        os.makedirs(output_folder, exist_ok=True)

        # Getting all text from all pages
        full_text = "\n".join([page.get_text() for page in doc])
        full_text = normalize(full_text)

        # Using OCR if we cannot properly decode PDF
        if garbage_text(full_text, threshold=0.5):
            images = convert_from_bytes(response.content)
            ocr_texts = []
            for img in images:
                text = pytesseract.image_to_string(img, lang="por")
                ocr_texts.append(text)
            full_text = "\n".join(ocr_texts)
            full_text = normalize(full_text)
            # Trimming document
            end_marker = "questionário de percepção da prova"
            end_index = full_text.rfind(end_marker)
            if end_index != -1:
                full_text = full_text[:end_index]

        # In case we don't need OCR, we need to get full text one page at a time to remove end_marker's page 
        else:
            end_marker = "questionário de percepção da prova"
            pages_before_marker = []
            for page in doc:
                raw = page.get_text()
                norm = normalize(raw)
                if end_marker in norm:
                    break
                pages_before_marker.append(raw)

            # Now joinning just those pages
            full_text = "\n".join(pages_before_marker)

        # Finding all question headers
        question_pattern = re.compile(r"(questão(?: discursiva)?\s+\d+)", re.IGNORECASE)

        matches = list(question_pattern.finditer(full_text))

        # Processing individual questions
        for i, match in enumerate(matches):
            question_title = match.group(1).lower()
            start_pos = match.end()

            # Defining end of current question
            end_pos = matches[i+1].start() if i+1 < len(matches) else len(full_text)

            # Extracting content
            question_text = full_text[start_pos:end_pos].strip()
            full_question = question_title + "\n" + question_text

            # Determining type (discursiva -> open or múltipla-escolha -> closed)
            is_open = "discursiva" in question_title
            q_type = "open" if is_open else "closed"
            q_number = re.findall(r"\d+", question_title)[0]

            # Saving to file
            filename = f"{q_type}_question_{q_number}.txt"
            filepath = os.path.join(output_folder, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(full_question)

            # print(f"Questão {q_number} ({q_type}) de {year} salva em: {filepath}")

        print(f"Extração das questões de prova de {year} completa: {len(matches)} questões salvas\n")

    except Exception as e:
        print(f"Não foi possível parsear o PDF {url}: {e}\n")

# Function to parse and extract content. Basically a wrapper of the other functions
def parse_and_extract(page, df, target_courses, extraction_type='edital'):
    # Getting all year tabs and filtering everything before 2014
    year_elements = page.locator(".govbr-tabs a").all()
    for year_element in year_elements:
        year = year_element.inner_text().strip()
        if not year.isdigit() or int(year) < 2014:
            continue

        # Simulating year click to extract information (and letting content load)
        year_element.click()
        time.sleep(1.5)

        # Selecting currently visible content block
        active_tab = page.locator(".tab-content.active")

        if extraction_type == 'edital':
            # Getting all <a> elements within it
            links = active_tab.locator("a").all()

            # Finding the target courses
            for link in links:
                link_text = normalize(link.inner_text())
                href = link.get_attribute("href")

                for course in list(target_courses.keys()):
                    if any(tc in link_text for tc in target_courses[course]):
                        print(f"Edital do curso {link_text} encontrado em {year}\n")
                        
                        if href.endswith(".pdf"):
                            theoretical_content = parse_pdf_theoretical(href, course, int(year))
                        else:
                            theoretical_content = parse_html_theoretical(href, course, int(year))
                        
                        # Populating dataframe
                        df['course'].append(course)
                        df['year'].append(year)
                        df['theoretical_content'].append(theoretical_content)

        elif extraction_type == 'prova':
            # Getting all <p> elements with class 'callout' inside the active tab
            callouts = active_tab.locator("p.callout").all()

            # Finding the target courses
            for callout in callouts:
                callout_text = normalize(callout.inner_text())

                for course in list(target_courses.keys()):
                    if any(tc in callout_text for tc in target_courses[course]):
                        # Look for the next sibling <ul>
                        ul_element = callout.locator("xpath=following-sibling::ul").first

                        # Now find <a> tags inside <li> elements under that <ul>
                        prova_links = ul_element.locator("li a").all()

                        # Now find the 'prova' link
                        for link in prova_links:
                            link_text = normalize(link.inner_text())
                            if link_text == 'prova':
                                href = link.get_attribute("href")
                                print(f"Prova do curso '{course}' encontrada em {year}\n")

                                test_content = parse_pdf_test(href, int(year))

    # Populating test_content with pd.NA because we are going to do this parsing on a GPU server so we can use and LLM to infer the area/sub-area of the content
    df['test_content'] = [pd.NA for y in df['year']]


# Starting interaction with browser
with sync_playwright() as p:
    # Choosing what courses to target
    target_courses = {'engenharia de computação': ["engenharia da computação", "engenharia de computação"]}

    # Initializing dataframe
    df = {'course': [], 'year': [], 'theoretical_content': [], 'test_content': []}

    # Launchung browser and navigating to desired URL
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    # Navigating to edital page
    url = "https://www.gov.br/inep/pt-br/centrais-de-conteudo/legislacao/enade"
    page.goto(url)
    reject_cookies(page)

    # Waiting for the the carousel containing years to load
    page.wait_for_selector(".govbr-tabs")

    # Parsing and extracting content from edital page
    parse_and_extract(page, df, target_courses, extraction_type='edital')

    # Repeating the process for the prova page
    url = "https://www.gov.br/inep/pt-br/areas-de-atuacao/avaliacao-e-exames-educacionais/enade/provas-e-gabaritos"
    page.goto(url)
    page.wait_for_selector(".govbr-tabs")
    parse_and_extract(page, df, target_courses, extraction_type='prova')

    browser.close()

    # Creating and saving dataframe
    df = pd.DataFrame(df)
    df.to_csv("data/enade_data.csv", index=False)