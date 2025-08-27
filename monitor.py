# -*- coding: utf-8 -*-
import os
import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone, timedelta
from urllib.parse import urljoin, urlparse

# --- CONFIGURAÇÃO ---
# URL do site a ser monitorado
URL_BASE = "http://www.saaesp.org.br/"

# Palavras-chave que indicam a notícia de interesse.
PALAVRAS_CHAVE = [
    "oposição", "carta de oposição", "prazo para oposição",
    "desconto sindical", "contribuição assistencial", "assembleia"
]

# Profundidade máxima de navegação a partir da página inicial
MAX_DEPTH = 5

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

def crawl_site(url, profundidade_atual):
    """
    Função recursiva que navega pelo site (crawler).
    """
    if profundidade_atual > MAX_DEPTH or url in urls_visitadas:
        return

    print(f"Analisando (Profundidade {profundidade_atual}): {url}")
    urls_visitadas.add(url)

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        texto_do_site = soup.get_text().lower()
        palavras_encontradas_pagina = [palavra for palavra in PALAVRAS_CHAVE if palavra.lower() in texto_do_site]
        
        if palavras_encontradas_pagina:
            print(f"  -> SUCESSO! Palavras encontradas: {', '.join(palavras_encontradas_pagina)}")
            paginas_com_achados.append({"url": url, "palavras": palavras_encontradas_pagina})

        for link in soup.find_all('a', href=True):
            href = link['href']
            url_absoluta = urljoin(URL_BASE, href)
            
            if urlparse(url_absoluta).netloc == urlparse(URL_BASE).netloc:
                crawl_site(url_absoluta, profundidade_atual + 1)

    except requests.exceptions.RequestException as e:
        print(f"  -> Erro ao acessar {url}: {e}")
    except Exception as e:
        print(f"  -> Ocorreu um erro inesperado em {url}: {e}")

def main():
    """
    Função principal que inicia o processo e envia o relatório final.
    """
    print(f"Iniciando verificação profunda do site: {URL_BASE}")
    crawl_site(URL_BASE, 1)
    
    # *** AJUSTE DE FUSO HORÁRIO IMPLEMENTADO AQUI ***
    # Define o fuso horário de São Paulo (GMT-3)
    fuso_horario_sp = timezone(timedelta(hours=-3))
    # Obtém a data e hora atuais já no fuso horário correto
    agora_sp = datetime.now(fuso_horario_sp)
    # Formata a data para o texto do e-mail
    data_verificacao = agora_sp.strftime('%d/%m/%Y %H:%M:%S')
    
    total_paginas = len(urls_visitadas)

    if paginas_com_achados:
        print("\n--- Relatório Final: Palavras-chave encontradas! ---")
        titulo_email = "ALERTA SAAESP: Informação sobre Carta de Oposição Encontrada!"
        
        links_html = ""
        for achado in paginas_com_achados:
            palavras_str = ", ".join(achado['palavras'])
            links_html += f"<li>Na página <a href='{achado['url']}'>{achado['url']}</a> foram encontradas as palavras: <strong>{palavras_str}</strong></li>"

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
