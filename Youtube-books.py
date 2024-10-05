import openai
import os

# Configurações de API
openai.api_key = "SUA_API_KEY_OPENAI"

# Definir o limite de tokens por requisição para o modelo (aproximadamente 4096 tokens por vez, ajustável)
LIMITE_TOKENS = 3500  # Mantendo uma margem de segurança


# Função para dividir o texto em partes respeitando o limite de tokens
def dividir_texto(texto, limite_tokens):
    partes = []
    palavras = texto.split()  # Dividimos o texto em palavras
    parte_atual = []
    total_tokens = 0

    for palavra in palavras:
        # Estimativa simples: 1 palavra ≈ 1 token (pode variar dependendo do conteúdo)
        total_tokens += 1
        parte_atual.append(palavra)

        if total_tokens >= limite_tokens:
            partes.append(' '.join(parte_atual))  # Adiciona a parte ao array
            parte_atual = []
            total_tokens = 0

    # Adicionar qualquer resto do texto que não completou um bloco
    if parte_atual:
        partes.append(' '.join(parte_atual))

    return partes


# Função para converter texto em áudio com a OpenAI
def texto_para_audio(texto, nome_arquivo_audio):
    response = openai.Audio.create(
        model="whisper-1",
        input={"prompt": texto, "language": "pt-BR"}  # Ajustar o idioma, se necessário
    )
    # Salvar o áudio recebido como MP3
    with open(nome_arquivo_audio, 'wb') as f:
        f.write(response['audio'])


# Função principal para processar o livro e gerar os áudios
def processar_livro(livro_path):
    # Extrair o nome do arquivo (sem extensão) para usar como nome da pasta de saída
    nome_livro = os.path.splitext(os.path.basename(livro_path))[0]

    # Criar a pasta de saída com o nome do livro
    pasta_saida = os.path.join(os.path.dirname(livro_path), nome_livro)
    if not os.path.exists(pasta_saida):
        os.makedirs(pasta_saida)

    # Ler o livro inteiro
    with open(livro_path, 'r', encoding='utf-8') as f:
        conteudo_livro = f.read()

    # Dividir o livro em partes menores
    partes_livro = dividir_texto(conteudo_livro, LIMITE_TOKENS)

    # Para cada parte, enviar para a OpenAI gerar o áudio e salvar
    for i, parte in enumerate(partes_livro):
        nome_arquivo_audio = os.path.join(pasta_saida, f"{nome_livro}_parte_{i + 1}.mp3")
        print(f"Gerando áudio para parte {i + 1} de {len(partes_livro)}...")

        # Chamar a API e salvar o arquivo
        texto_para_audio(parte, nome_arquivo_audio)

        print(f"Áudio da parte {i + 1} salvo em: {nome_arquivo_audio}")


# Função para processar todos os livros na pasta 'books'
def processar_livros_na_pasta(pasta_livros):
    # Listar todos os arquivos de texto na pasta
    for arquivo in os.listdir(pasta_livros):
        if arquivo.endswith('.txt'):
            livro_path = os.path.join(pasta_livros, arquivo)
            print(f"Processando livro: {arquivo}")
            processar_livro(livro_path)


# Definir o caminho da pasta 'books'
pasta_books = "caminho/para/sua/pasta/books"

# Processar todos os livros na pasta
processar_livros_na_pasta(pasta_books)
