import docx
from collections import Counter
from googletrans import Translator
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import re
import requests
import json

# Baixar recursos necessários do NLTK
nltk.download('punkt', quiet=True)
nltk.download('stopwords', quiet=True)

def generate_example_sentences(word_pairs, num_sentences=1):
    """
    Gera frases de exemplo usando o Ollama para cada par de palavras traduzidas.

    Args:
        word_pairs: Lista de tuplas (palavra_pt, palavra_en)
        num_sentences: Número de frases para cada par de palavras
    """
    example_sentences = []

    for pt_word, en_word in word_pairs:
        prompt = f"""Generate {num_sentences} simple example sentence(s) in English using the word '{en_word}' (which is the translation of the Portuguese word '{pt_word}'). 
        Make the sentence easy to understand for a Portuguese speaker learning English.
        Format: Just return the sentence(s), one per line."""

        # Configuração da requisição para o Ollama
        url = "http://localhost:11434/api/generate"
        data = {
            "model": "llama3.2:latest",
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9
            }
        }

        try:
            # Verificar se o Ollama está rodando
            health_check = requests.get("http://localhost:11434/api/tags")
            if health_check.status_code != 200:
                raise Exception("Ollama server is not running")

            response = requests.post(url, json=data)
            if response.status_code == 200:
                response_data = response.json()
                sentences = response_data['response'].strip().split('\n')
                for sentence in sentences:
                    example_sentences.append({
                        'pt_word': pt_word,
                        'en_word': en_word,
                        'sentence': sentence.strip()
                    })
            else:
                print(f"Erro ao gerar frase para {pt_word}/{en_word}: Status code {response.status_code}")
                print(f"Response: {response.text}")
        except requests.exceptions.ConnectionError:
            print(
                f"Erro de conexão com o Ollama. Certifique-se de que o servidor está rodando em http://localhost:11434")
            return example_sentences
        except Exception as e:
            print(f"Erro ao gerar frase para {pt_word}/{en_word}: {str(e)}")

    return example_sentences

def read_docx(file_path):
    """Lê o arquivo .docx e retorna o texto completo."""
    doc = docx.Document(file_path)
    full_text = []
    for para in doc.paragraphs:
        full_text.append(para.text)
    return ' '.join(full_text)

def is_valid_word(word):
    """Verifica se a palavra é válida (somente alfanumérica e não contém caracteres especiais)."""
    return bool(re.match(r'^[A-Za-zÀ-ÿ0-9]+$', word))

def get_top_words(text, n=100):
    """Obtém as n palavras mais comuns do texto, excluindo stopwords."""
    tokens = word_tokenize(text.lower())
    stop_words = set(stopwords.words('portuguese'))
    tokens = [word for word in tokens if is_valid_word(word) and word not in stop_words]
    word_counts = Counter(tokens)
    return word_counts.most_common(n)

def translate_word(word):
    """Traduz uma única palavra usando o Google Translate."""
    translator = Translator()
    try:
        return translator.translate(word, src='pt', dest='en').text
    except Exception as e:
        print(f"Erro ao traduzir '{word}': {e}")
        return None

def replace_word_in_doc(doc, word, translation):
    """
    Substitui a palavra no documento pelo seu equivalente em inglês em negrito,
    garantindo que seja uma correspondência exata e ignorando maiúsculas/minúsculas.
    """
    for para in doc.paragraphs:
        original_text = para.text

        if word.lower() not in original_text.lower():
            continue

        for run in para.runs:
            run.clear()

        parts = re.split(rf'(\b{word}\b)', original_text, flags=re.IGNORECASE)

        para.clear()
        for part in parts:
            if part.lower() == word.lower():
                run = para.add_run(translation)
                run.bold = True
            else:
                run = para.add_run(part)

    return doc

def generate_interactive_story(top_words):
    """
    Gera uma história interativa com base nas 200 palavras mais usadas no texto.
    """
    story = "Era uma vez um mundo onde as palavras ganhavam vida. "

    for word, _ in top_words:
        translation = translate_word(word)
        if translation:
            story += f"Uma vez, a palavra '{word}' encontrou seu amigo '{translation}'. "

    story += "E juntos, eles viajaram por muitas terras, aprendendo novas palavras e fazendo novas descobertas."

    return story

def process_file(file_path, num_words=200):
    """Processa o arquivo .docx especificado."""
    # Ler o documento
    text = read_docx(file_path)

    # Obter as n palavras mais comuns
    top_words = get_top_words(text, num_words)

    # Traduzir e substituir as palavras no documento
    new_doc = docx.Document(file_path)
    translated_words = {}
    word_pairs = []  # Lista para armazenar pares de palavras (pt, en)

    for word, _ in top_words:
        if is_valid_word(word):
            translation = translate_word(word)
            if translation:
                translated_words[word] = translation
                word_pairs.append((word, translation))
                new_doc = replace_word_in_doc(new_doc, word, translation)

    # Gerar frases de exemplo usando o Ollama
    print("Gerando frases de exemplo...")
    example_sentences = generate_example_sentences(word_pairs)

    # Criar uma lista das palavras traduzidas com frases de exemplo
    translated_words_list = []
    for word, translation in translated_words.items():
        translated_words_list.append(f"{word} - {translation}")

    # Adicionar a lista de palavras traduzidas e frases ao documento
    new_doc.add_paragraph("\nLista de palavras traduzidas:").bold = True
    for translated_word in translated_words_list:
        paragraph = new_doc.add_paragraph()
        word, translation = translated_word.split(" - ")
        paragraph.add_run(f"{word} - ").bold = False
        paragraph.add_run(f"{translation}").bold = True

        # Adicionar frases de exemplo para esta palavra
        sentences = [s['sentence'] for s in example_sentences if s['pt_word'] == word]
        if sentences:
            for sentence in sentences:
                example_para = new_doc.add_paragraph()
                example_para.add_run("Example: ").italic = True
                example_para.add_run(sentence)

    # Gerar uma história interativa com as palavras mais comuns
    interactive_story = generate_interactive_story(top_words)
    new_doc.add_paragraph("\nHistória interativa gerada com as palavras mais comuns:")
    new_doc.add_paragraph(interactive_story)

    # Salvar o novo documento
    new_file_name = 'docsx/ativo/O Pequeno Principe - Antoine de Saint-Exupery-A0.docx'
    new_doc.save(new_file_name)
    print(f"Processado: {file_path} -> {new_file_name}")

# Caminho do arquivo .docx a ser processado
file_path = 'docsx/ativo/O Pequeno Principe - Antoine de Saint-Exupery.docx'
num_words = 200  # Número de palavras mais comuns a serem obtidas

process_file(file_path, num_words)
print("Processo concluído.")
