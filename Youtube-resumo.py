import os
import openai
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# Configuração da API
openai.api_key = os.getenv("OPENAI_API_KEY")


def gerar_resumo(texto):
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "Você é um assistente útil que resume livros inteiros."},
            {"role": "user", "content": f"Resuma o seguinte livro: {texto}"}
        ]
    )
    return response.choices[0].message['content']


def texto_para_audio(texto, nome_arquivo):
    response = openai.audio.speech.create(
        model="tts-1",
        voice="nova",  # Você pode escolher entre "alloy", "echo", "fable", "onyx", "nova", ou "shimmer"
        input=texto
    )
    response.stream_to_file(nome_arquivo)


def ler_arquivo(caminho_arquivo):
    with open(caminho_arquivo, 'r', encoding='utf-8') as f:
        return f.read()


def processar_arquivo(caminho_arquivo):
    nome_arquivo = os.path.basename(caminho_arquivo)
    nome_livro = os.path.splitext(nome_arquivo)[0]

    conteudo = ler_arquivo(caminho_arquivo)
    resumo = gerar_resumo(conteudo)
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
    pasta_livro = "books"
    processar_pasta_livros(pasta_livro)