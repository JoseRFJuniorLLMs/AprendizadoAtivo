import docx
from collections import Counter
from googletrans import Translator
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import re
import requests
from tqdm import tqdm

# Baixar recursos necessários do NLTK
nltk.download('punkt', quiet=True)
nltk.download('stopwords', quiet=True)


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
    print("Analisando palavras mais comuns...")
    tokens = word_tokenize(text.lower())
    stop_words = set(stopwords.words('portuguese'))
    tokens = [word for word in tokens if is_valid_word(word) and word not in stop_words]
    word_counts = Counter(tokens)
    print(f"Encontradas {len(tokens)} palavras válidas.")
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
    """Substitui a palavra no documento pelo seu equivalente em inglês em negrito."""
    for para in doc.paragraphs:
        if word.lower() in para.text.lower():
            runs = para.runs
            new_runs = []
            for run in runs:
                parts = re.split(rf'(\b{word}\b)', run.text, flags=re.IGNORECASE)
                for part in parts:
                    if part.lower() == word.lower():
                        new_run = para.add_run(translation)
                        new_run.bold = True
                        new_runs.append(new_run)
                    else:
                        new_run = para.add_run(part)
                        new_run.bold = run.bold
                        new_run.italic = run.italic
                        new_run.underline = run.underline
                        new_runs.append(new_run)
            para.clear()
            for new_run in new_runs:
                para.add_run(new_run.text)
    return doc


def process_file(file_path, num_words=200):
    """Processa o arquivo .docx especificado."""
    print(f"Iniciando o processamento do arquivo: {file_path}")
    print("Lendo o arquivo...")
    text = read_docx(file_path)

    print("Obtendo as palavras mais comuns...")
    top_words = get_top_words(text, num_words)

    print("Traduzindo palavras e substituindo no documento...")
    new_doc = docx.Document(file_path)
    translated_words = {}
    word_pairs = []

    with tqdm(total=len(top_words), desc="Traduzindo e substituindo palavras") as pbar:
        for word, _ in top_words:
            if is_valid_word(word):
                translation = translate_word(word)
                if translation:
                    translated_words[word] = translation
                    word_pairs.append((word, translation))
                    new_doc = replace_word_in_doc(new_doc, word, translation)
            pbar.update(1)

    print("Adicionando palavras traduzidas ao final do documento...")
    new_doc.add_paragraph("\nLista de palavras traduzidas:").bold = True
    for word, translation in translated_words.items():
        paragraph = new_doc.add_paragraph()
        paragraph.add_run(f"{word} - ").bold = False
        paragraph.add_run(f"{translation}").bold = True

    new_file_name = 'docsx/ativo/Capitaes da Areia - Jorge Amado-A0.docx'
    new_doc.save(new_file_name)
    print(f"Processado: {file_path} -> {new_file_name}")


# Caminho do arquivo .docx a ser processado
file_path = 'docsx/ativo/Capitaes da Areia - Jorge Amado.docx'
num_words = 200  # Número de palavras mais comuns a serem obtidas

process_file(file_path, num_words)
print("Processo concluído.")
