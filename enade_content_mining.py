import time
import re
import os
import io

from playwright.sync_api import sync_playwright
import fitz
from bs4 import BeautifulSoup
import pandas as pd
import requests

# Choosing what courses to target
target_courses = {'engenharia de computação': ["engenharia da computação", "engenharia de computação"]}

df = {'course': [], 'year': [], 'theoretical_content': [], 'test_content': []}

# Normalizing text for when we want to compare strings
def normalize(text):
    return text.strip().lower()

# Parsing PDF to extract ENADE theoretical content
def parse_pdf_theoretical(url, course, year):
    try:
        # Getting PDF
        response = requests.get(url)
        pdf_stream = io.BytesIO(response.content)
        doc = fitz.open(stream=pdf_stream, filetype="pdf")

        # Finding all lines of the HTML and accumulating contents for Art. 6 or 7
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

        return content_list

    except Exception as e:
        print(f"Não foi possível parsear o PDF {url}: {e}\n")
        return []

# Parsing HTML to extract ENADE theoretical content
def parse_html_theoretical(url, course, year):
    try:
        # Getting HTML
        response = requests.get(url)
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

        return content_list

    except Exception as e:
        print(f"Não foi possível parsear o HTML {url}: {e}\n")
        return []

# Starting interaction with browser
with sync_playwright() as p:
    # Launchung browser and navigating to desired URL
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    url = "https://www.gov.br/inep/pt-br/centrais-de-conteudo/legislacao/enade"
    page.goto(url)
    
    # Clicking to reject cookies
    try:
        page.wait_for_selector("button:has-text('Rejeitar cookies')", timeout=5000)
        page.click("button:has-text('Rejeitar cookies')")
    except:
        print("Aba de cookies não apareceu?\n")

    # Waiting for the the carousel containing years to load
    page.wait_for_selector(".govbr-tabs")

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

        # Getting all <a> elements within it
        links = active_tab.locator("a").all()

        # Finding the target courses
        for link in links:
            link_text = normalize(link.inner_text())
            href = link.get_attribute("href")

            for course in list(target_courses.keys()):
                if any(tc in link_text for tc in target_courses[course]):
                    print(f"Curso {link_text} encontrado em {year}\n")
                    
                    if href.endswith(".pdf"):
                        theoretical_content = parse_pdf_theoretical(href, course, int(year))
                    else:
                        theoretical_content = parse_html_theoretical(href, course, int(year))
                    
                    df['course'].append(course)
                    df['year'].append(year)
                    df['theoretical_content'].append(theoretical_content)

                    break

    print(df)

    browser.close()
