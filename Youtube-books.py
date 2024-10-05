import os
import openai
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# Configuração da API
openai.api_key = os.getenv("OPENAI_API_KEY")

def texto_para_audio(texto, nome_arquivo):
    try:
        response = openai.audio.speech.create(
            model="tts-1",  # Modelo para texto para fala
            voice="alloy",  # Você pode escolher outra voz se desejar
            input=texto
        )

        # Salva o arquivo de áudio
        with open(nome_arquivo, "wb") as f:
            f.write(response.content)
        print(f"Áudio salvo em: {nome_arquivo}")

    except openai.error.OpenAIError as e:
        print(f"Erro na API OpenAI: {e}")
    except Exception as e:
        print(f"Ocorreu um erro ao converter texto para áudio: {e}")


def ler_arquivo(caminho_arquivo):
    with open(caminho_arquivo, 'r', encoding='utf-8') as f:
        return f.read()


def processar_arquivo(caminho_arquivo):
    nome_arquivo = os.path.basename(caminho_arquivo)
    nome_livro = os.path.splitext(nome_arquivo)[0]

    conteudo = ler_arquivo(caminho_arquivo)

    # Dividir o texto em partes menores (idealmente testar com < 1000 caracteres)
    partes = [conteudo[i:i + 1000] for i in range(0, len(conteudo), 1000)]

    # Gerar áudio para cada parte
    for index, parte in enumerate(partes):
        nome_arquivo_audio = f"{nome_livro}_parte_{index + 1}.mp3"
        caminho_audio = os.path.join(os.path.dirname(caminho_arquivo), nome_arquivo_audio)
        texto_para_audio(parte, caminho_audio)


def processar_pasta_livros(pasta_livro):
    for arquivo in os.listdir(pasta_livro):
        if arquivo.endswith(".txt"):
            caminho_arquivo = os.path.join(pasta_livro, arquivo)
            processar_arquivo(caminho_arquivo)

if __name__ == "__main__":
    pasta_livro = "books"  # A pasta onde estão os livros
    processar_pasta_livros(pasta_livro)