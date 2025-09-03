# -*- coding: utf-8 -*-
import os
import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone, timedelta
from urllib.parse import urljoin, urlparse
import time

# --- NOVO: Importações do Selenium ---
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from webdriver_manager.chrome import ChromeDriverManager


# --- CONFIGURAÇÃO ---
URL_BASE = "http://www.saaesp.org.br/"
PALAVRAS_CHAVE = [
    "oposição", "carta de oposição", "prazo para oposição",
    "desconto sindical", "contribuição assistencial", "assembleia"
]
# Profundidade aumentada para 6
MAX_DEPTH = 6

# --- CONFIGURAÇÃO DO E-MAIL (lido das variáveis de ambiente/secrets) ---
REMETENTE_EMAIL = os.environ.get('REMETENTE_EMAIL')
SENHA_EMAIL = os.environ.get('SENHA_EMAIL')
DESTINATARIO_EMAIL = os.environ.get('DESTINATARIO_EMAIL')
SERVIDOR_SMTP = "smtp.gmail.com"
PORTA_SMTP = 587

# --- VARIÁVEIS GLOBAIS DO CRAWLER ---
urls_visitadas = set()
paginas_com_achados = []

def enviar_email(titulo, corpo_html):
    """
    Função para enviar um e-mail de notificação ou relatório.
    """
    if not all([REMETENTE_EMAIL, SENHA_EMAIL, DESTINATARIO_EMAIL]):
        print("ERRO: As variáveis de ambiente para e-mail não foram configuradas.")
        return

    print(f"Preparando e-mail para {DESTINATARIO_EMAIL}...")
    try:
        msg = MIMEMultipart()
        msg['From'] = REMETENTE_EMAIL
        msg['To'] = DESTINATARIO_EMAIL
        msg['Subject'] = titulo
        msg.attach(MIMEText(corpo_html, 'html'))

        server = smtplib.SMTP(SERVIDOR_SMTP, PORTA_SMTP)
        server.starttls()
        server.login(REMETENTE_EMAIL, SENHA_EMAIL)
        server.sendmail(REMETENTE_EMAIL, DESTINATARIO_EMAIL, msg.as_string())
        server.quit()
        print("E-mail enviado com sucesso!")
    except Exception as e:
        print(f"Falha ao enviar e-mail: {e}")

def crawl_site(url, profundidade_atual, driver):
    """
    Função recursiva que navega pelo site usando Selenium para renderizar JavaScript.
    """
    if profundidade_atual > MAX_DEPTH or url in urls_visitadas:
        return

    print(f"Analisando (Profundidade {profundidade_atual}): {url}")
    urls_visitadas.add(url)

    try:
        # Selenium carrega a página e executa o JavaScript
        driver.get(url)
        # Uma pequena espera para garantir que os scripts rodem
        time.sleep(3) 
        
        # Pega o HTML final, depois do JS
        html_content = driver.page_source
        soup = BeautifulSoup(html_content, 'html.parser')
        
        texto_do_site = soup.get_text().lower()
        palavras_encontradas_pagina = [palavra for palavra in PALAVRAS_CHAVE if palavra.lower() in texto_do_site]
        
        if palavras_encontradas_pagina:
            palavras_str = ", ".join(palavras_encontradas_pagina)
            print(f"  -> SUCESSO! Palavras encontradas: {palavras_str}")
            # Adiciona na lista de achados, evitando duplicatas
            if not any(d['url'] == url for d in paginas_com_achados):
                paginas_com_achados.append({"url": url, "palavras": list(set(palavras_encontradas_pagina))})

        for link in soup.find_all('a', href=True):
            href = link['href']
            url_absoluta = urljoin(URL_BASE, href)
            
            # Garante que estamos navegando apenas dentro do site original
            if urlparse(url_absoluta).netloc == urlparse(URL_BASE).netloc:
                crawl_site(url_absoluta, profundidade_atual + 1, driver)

    except Exception as e:
        print(f"  -> Ocorreu um erro inesperado em {url}: {e}")

def main():
    """
    Função principal que inicia o processo e envia o relatório final.
    """
    print("Configurando o navegador headless (Chrome)...")
    chrome_options = ChromeOptions()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # webdriver-manager instala e gerencia o driver do Chrome automaticamente
    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    print(f"Iniciando verificação profunda do site: {URL_BASE}")
    crawl_site(URL_BASE, 1, driver)
    
    # Fecha o navegador ao final da verificação
    driver.quit()
    
    fuso_horario_sp = timezone(timedelta(hours=-3))
    agora_sp = datetime.now(fuso_horario_sp)
    data_verificacao = agora_sp.strftime('%d/%m/%Y %H:%M:%S')
    total_paginas = len(urls_visitadas)

    # Lógica de e-mail (permanece a mesma)
    if paginas_com_achados:
        print("\n--- Relatório Final: Palavras-chave encontradas! ---")
        titulo_email = "ALERTA SAAESP: Informação sobre Carta de Oposição Encontrada!"
        links_html = "".join([f"<li>Na página <a href='{achado['url']}'>{achado['url']}</a> foram encontradas as palavras: <strong>{', '.join(achado['palavras'])}</strong></li>" for achado in paginas_com_achados])
        corpo_html = f"""
        <html><body>
            <h2>Alerta de Monitoramento Automático</h2>
            <p>Olá,</p>
            <p>O agente de monitoramento <strong>ENCONTROU</strong> uma ou mais palavras-chave de interesse no site do SAAESP.</p>
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
        titulo_email = f"Relatório SAAESP: Nenhuma Novidade Encontrada Hoje"
        corpo_html = f"""
        <html><body>
            <h2>Relatório Diário de Monitoramento</h2>
            <p>Olá,</p>
            <p>O agente de monitoramento concluiu a verificação no site do SAAESP e <strong>NÃO ENCONTROU</strong> nenhuma das palavras-chave de interesse.</p>
            <p><strong>Data da Verificação:</strong> {data_verificacao}</p>
            <p><strong>Total de Páginas Verificadas:</strong> {total_paginas}</p>
            <p>Nenhuma ação é necessária. O agente continua monitorando diariamente.</p>
            <br><p><em>Este é um e-mail automático.</em></p>
        </body></html>
        """
    
    enviar_email(titulo_email, corpo_html)

if __name__ == "__main__":
    main()
