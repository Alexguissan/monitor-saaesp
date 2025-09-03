# -*- coding: utf-8 -*-
import os
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timezone, timedelta
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

# --- CONFIGURAÇÃO ---
URL_BASE = "http://www.saaesp.org.br/"
PALAVRAS_CHAVE = [
    "oposição", "carta de oposição", "prazo para oposição",
    "desconto sindical", "contribuição assistencial", "assembleia"
]
MAX_DEPTH = 6

# --- CONFIGURAÇÃO DO E-MAIL ---
REMETENTE_EMAIL = os.environ.get('REMETENTE_EMAIL')
SENHA_EMAIL = os.environ.get('SENHA_EMAIL')
DESTINATARIO_EMAIL = os.environ.get('DESTINATARIO_EMAIL')
SERVIDOR_SMTP = "smtp.gmail.com"
PORTA_SMTP = 587

# --- VARIÁVEIS GLOBAIS ---
urls_visitadas = set()
paginas_com_achados = []

def enviar_email(titulo, corpo_html):
    """Envia um e-mail de notificação ou relatório."""
    if not all([REMETENTE_EMAIL, SENHA_EMAIL, DESTINATARIO_EMAIL]):
        print("ERRO: Variáveis de ambiente para e-mail não configuradas.")
        return

    print(f"Preparando e-mail para {DESTINATARIO_EMAIL}...")
    try:
        msg = MIMEMultipart()
        msg['From'] = REMETENTE_EMAIL
        msg['To'] = DESTINATARIO_EMAIL
        msg['Subject'] = titulo
        msg.attach(MIMEText(corpo_html, 'html', 'utf-8'))

        server = smtplib.SMTP(SERVIDOR_SMTP, PORTA_SMTP)
        server.starttls()
        server.login(REMETENTE_EMAIL, SENHA_EMAIL)
        server.sendmail(REMETENTE_EMAIL, DESTINATario_EMAIL, msg.as_string())
        server.quit()
        print("E-mail enviado com sucesso!")
    except Exception as e:
        print(f"Falha ao enviar e-mail: {e}")

def crawl_site(url, profundidade_atual, driver):
    """Navega recursivamente pelo site, extraindo links de forma ativa."""
    if profundidade_atual > MAX_DEPTH or url in urls_visitadas:
        return

    print(f"Analisando (Profundidade {profundidade_atual}): {url}")
    urls_visitadas.add(url)

    try:
        driver.get(url)
        wait = WebDriverWait(driver, 30)

        # Espera robusta pelo rodapé, indicando que a página está 'montada'
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "div[data-elementor-type='footer']")))
        time.sleep(3)  # Pausa final para garantir renderização de scripts

        # Análise de texto com BeautifulSoup (após a página estar carregada)
        html_content = driver.page_source
        soup = BeautifulSoup(html_content, 'html.parser')
        texto_do_site = soup.get_text().lower()
        
        palavras_encontradas_pagina = [p for p in PALAVRAS_CHAVE if p.lower() in texto_do_site]
        if palavras_encontradas_pagina:
            palavras_str = ", ".join(set(palavras_encontradas_pagina))
            print(f"  -> SUCESSO! Palavras encontradas: {palavras_str}")
            if not any(d['url'] == url for d in paginas_com_achados):
                paginas_com_achados.append({"url": url, "palavras": list(set(palavras_encontradas_pagina))})

        # --- MUDANÇA CRÍTICA: Extração ativa de links via Selenium ---
        link_elements = driver.find_elements(By.TAG_NAME, 'a')
        links_encontrados = []
        for link_el in link_elements:
            href = link_el.get_attribute('href')
            if href and not href.startswith(('javascript:', '#', 'mailto:')):
                links_encontrados.append(href)
        
        print(f"  -> Encontrados {len(links_encontrados)} links válidos na página.")

        for href in links_encontrados:
            url_absoluta = urljoin(URL_BASE, href)
            # Garante que estamos navegando apenas dentro do domínio do site
            if urlparse(url_absoluta).netloc == urlparse(URL_BASE).netloc:
                crawl_site(url_absoluta, profundidade_atual + 1, driver)

    except TimeoutException:
        print(f"  -> ERRO: Tempo de espera esgotado em {url}. Página muito lenta ou offline.")
    except Exception as e:
        print(f"  -> Ocorreu um erro inesperado em {url}: {e}")

def main():
    """Função principal que orquestra o processo."""
    print("Configurando o navegador headless (Chrome)...")
    chrome_options = ChromeOptions()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("window-size=1920,1080")

    try:
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
    except Exception as e:
        print(f"ERRO CRÍTICO ao iniciar o WebDriver: {e}")
        enviar_email("ERRO no Agente SAAESP", f"<html><body>Não foi possível iniciar o navegador. Erro: {e}</body></html>")
        return

    print(f"Iniciando verificação profunda do site: {URL_BASE}")
    crawl_site(URL_BASE, 1, driver)
    driver.quit()

    fuso_horario_sp = timezone(timedelta(hours=-3))
    data_verificacao = datetime.now(fuso_horario_sp).strftime('%d/%m/%Y %H:%M:%S')
    total_paginas = len(urls_visitadas)
    
    # Montagem do relatório final
    if paginas_com_achados:
        print("\n--- Relatório Final: Palavras-chave encontradas! ---")
        titulo_email = "ALERTA SAAESP: Informação sobre Carta de Oposição Encontrada!"
        links_html = "".join([f"<li>Na página <a href='{a['url']}'>{a['url']}</a>: <strong>{', '.join(a['palavras'])}</strong></li>" for a in paginas_com_achados])
        corpo_html = f"""
        <html><body>
            <h2>Alerta de Monitoramento Automático</h2>
            <p>Olá,</p>
            <p>O agente de monitoramento <strong>ENCONTROU</strong> uma ou mais palavras-chave no site do SAAESP.</p>
            <p><strong>Data da Verificação:</strong> {data_verificacao}</p>
            <p><strong>Total de Páginas Verificadas:</strong> {total_paginas}</p>
            <h3>Detalhes dos Achados:</h3>
            <ul>{links_html}</ul>
            <p>Acesse os links acima para confirmar. É provável que o prazo para a carta de oposição tenha sido divulgado.</p>
            <br><p><em>Este é um e-mail automático.</em></p>
        </body></html>
        """
    else:
        print("\n--- Relatório Final: Nenhuma palavra-chave encontrada. ---")
        titulo_email = "Relatório SAAESP: Nenhuma Novidade Encontrada Hoje"
        corpo_html = f"""
        <html><body>
            <h2>Relatório Diário de Monitoramento</h2>
            <p>Olá,</p>
            <p>O agente de monitoramento concluiu a verificação e <strong>NÃO ENCONTROU</strong> palavras-chave de interesse.</p>
            <p><strong>Data da Verificação:</strong> {data_verificacao}</p>
            <p><strong>Total de Páginas Verificadas:</strong> {total_paginas}</p>
            <p>Nenhuma ação é necessária. O agente continua monitorando diariamente.</p>
            <br><p><em>Este é um e-mail automático.</em></p>
        </body></html>
        """
    
    enviar_email(titulo_email, corpo_html)

if __name__ == "__main__":
    main()

