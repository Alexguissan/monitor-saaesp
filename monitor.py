# -*- coding: utf-8 -*-
import os
import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import datetime

# --- CONFIGURAÇÃO ---
# URL do site a ser monitorado
URL_SITE = "http://www.saaesp.org.br/"

# Palavras-chave que indicam a notícia de interesse.
# O script vai procurar por QUALQUER uma dessas palavras.
PALAVRAS_CHAVE = [
    "oposição", "carta de oposição", "prazo para oposição",
    "desconto sindical", "contribuição assistencial", "assembleia"
]

# --- CONFIGURAÇÃO DO E-MAIL (será lido das variáveis de ambiente/secrets) ---
# Use os Secrets do GitHub para armazenar isso de forma segura
REMETENTE_EMAIL = os.environ.get('REMETENTE_EMAIL')
SENHA_EMAIL = os.environ.get('SENHA_EMAIL') # Use uma "Senha de App" se usar Gmail com 2FA
DESTINATARIO_EMAIL = os.environ.get('DESTINATARIO_EMAIL')
SERVIDOR_SMTP = "smtp.gmail.com" # Exemplo para Gmail
PORTA_SMTP = 587

def enviar_email(titulo, corpo_html):
    """
    Função para enviar um e-mail de notificação.
    """
    if not all([REMETENTE_EMAIL, SENHA_EMAIL, DESTINATARIO_EMAIL]):
        print("ERRO: As variáveis de ambiente para e-mail não foram configuradas.")
        return

    print(f"Enviando notificação por e-mail para {DESTINATARIO_EMAIL}...")

    try:
        # Configuração da mensagem
        msg = MIMEMultipart()
        msg['From'] = REMETENTE_EMAIL
        msg['To'] = DESTINATARIO_EMAIL
        msg['Subject'] = titulo
        msg.attach(MIMEText(corpo_html, 'html'))

        # Conexão com o servidor SMTP
        server = smtplib.SMTP(SERVIDOR_SMTP, PORTA_SMTP)
        server.starttls()  # Habilita segurança
        server.login(REMETENTE_EMAIL, SENHA_EMAIL)
        texto = msg.as_string()
        server.sendmail(REMETENTE_EMAIL, DESTINATARIO_EMAIL, texto)
        server.quit()

        print("E-mail de notificação enviado com sucesso!")
    except Exception as e:
        print(f"Falha ao enviar e-mail: {e}")

def verificar_site():
    """
    Função principal que verifica o site em busca das palavras-chave.
    """
    print(f"Iniciando verificação do site: {URL_SITE}")
    try:
        # Faz a requisição para obter o conteúdo da página
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
        response = requests.get(URL_SITE, headers=headers, timeout=30)
        response.raise_for_status()  # Lança um erro se a requisição falhar

        # Analisa o HTML da página
        soup = BeautifulSoup(response.content, 'html.parser')
        texto_do_site = soup.get_text().lower() # Pega todo o texto e converte para minúsculas

        palavras_encontradas = []
        # Verifica se alguma das palavras-chave está no texto do site
        for palavra in PALAVRAS_CHAVE:
            if palavra.lower() in texto_do_site:
                palavras_encontradas.append(palavra)

        if palavras_encontradas:
            print(f"SUCESSO! Palavras-chave encontradas: {', '.join(palavras_encontradas)}")
            
            # Monta o corpo do e-mail
            titulo_email = "Alerta SAAESP: Possível Informação sobre Carta de Oposição Encontrada!"
            corpo_html = f"""
            <html>
            <body>
                <h2>Alerta de Monitoramento Automático</h2>
                <p>Olá,</p>
                <p>O agente de monitoramento encontrou uma ou mais palavras-chave de interesse no site do SAAESP.</p>
                <p><strong>Data da Verificação:</strong> {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
                <p><strong>Palavras Encontradas:</strong> {', '.join(palavras_encontradas)}</p>
                <p>Isso pode indicar a abertura do prazo para a entrega da carta de oposição ao desconto sindical.</p>
                <p><strong>Acesse o site imediatamente para confirmar:</strong></p>
                <p><a href="{URL_SITE}" style="font-size: 16px; padding: 10px 20px; background-color: #007BFF; color: white; text-decoration: none; border-radius: 5px;">Verificar SAAESP.org.br</a></p>
                <br>
                <p><em>Este é um e-mail automático enviado pelo seu agente de monitoramento.</em></p>
            </body>
            </html>
            """
            enviar_email(titulo_email, corpo_html)
        else:
            print("Nenhuma palavra-chave encontrada na verificação de hoje.")

    except requests.exceptions.RequestException as e:
        print(f"Erro ao acessar o site: {e}")
    except Exception as e:
        print(f"Ocorreu um erro inesperado: {e}")

if __name__ == "__main__":
    verificar_site()
