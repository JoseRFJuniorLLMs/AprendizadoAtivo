import os
import openai
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# Configuração da API
openai.api_key = os.getenv("OPENAI_API_KEY")  # Certifique-se de que a variável OPENAI_API_KEY está configurada no .env

def gerar_resumo(texto):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # ou "gpt-4", se você tiver acesso
            messages=[
                {"role": "system", "content": "Você é um assistente útil que resume livros inteiros."},
                {"role": "user", "content": f"Resuma os capítulos do seguinte livro: {texto}"}
            ]
        )
        return response['choices'][0]['message']['content']  # Acesso correto à resposta
    except Exception as e:
        print(f"Ocorreu um erro ao gerar o resumo: {e}")
        return None

def texto_para_audio(texto, nome_arquivo):
    try:
        response = openai.Audio.create(
            model="text-to-speech-1",
            voice="nova",  # Você pode escolher entre "alloy", "echo", "fable", "onyx", "nova", ou "shimmer"
            input=texto
        )
        with open(nome_arquivo, "wb") as f:
            f.write(response['data'])  # Corrigido para acessar o conteúdo
    except Exception as e:
        print(f"Ocorreu um erro ao converter texto para áudio: {e}")

def ler_arquivo(caminho_arquivo):
    with open(caminho_arquivo, 'r', encoding='utf-8') as f:
        return f.read()

def processar_arquivo(caminho_arquivo):
    nome_arquivo = os.path.basename(caminho_arquivo)
    nome_livro = os.path.splitext(nome_arquivo)[0]

    conteudo = ler_arquivo(caminho_arquivo)
    resumo = gerar_resumo(conteudo)

    if resumo:  # Verifica se o resumo foi gerado com sucesso
        print(f"Resumo completo do livro '{nome_livro}': {resumo}")

        nome_arquivo_audio = f"{nome_livro}_resumo.mp3"
        caminho_audio = os.path.join(os.path.dirname(caminho_arquivo), nome_arquivo_audio)
        texto_para_audio(resumo, caminho_audio)
        print(f"Áudio do resumo salvo em: {caminho_audio}")

def processar_pasta_livros(pasta_livro):
    for arquivo in os.listdir(pasta_livro):
        if arquivo.endswith(".txt"):
            caminho_arquivo = os.path.join(pasta_livro, arquivo)
            processar_arquivo(caminho_arquivo)

if __name__ == "__main__":
    pasta_livro = "books"  # Certifique-se de que esta pasta existe e contém arquivos .txt
    processar_pasta_livros(pasta_livro)
