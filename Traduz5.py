import docx
from collections import Counter
from googletrans import Translator
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import re
import requests
from tqdm import tqdm  # Biblioteca para barra de progresso

# Baixar recursos necessários do NLTK
nltk.download('punkt', quiet=True)
nltk.download('stopwords', quiet=True)


def generate_example_sentences(word_pairs, num_sentences=1):
    """Gera frases de exemplo usando o Ollama para cada par de palavras traduzidas."""
    example_sentences = []
    for pt_word, en_word in tqdm(word_pairs, desc="Gerando frases de exemplo"):
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
            print(f"Erro de conexão com o Ollama. Certifique-se de que o servidor está rodando em http://localhost:11434")
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
    """Substitui a palavra no documento pelo seu equivalente em inglês em negrito."""
    for para in doc.paragraphs:
        new_runs = []
        i = 0
        while i < len(para.runs):
            run_text = para.runs[i].text
            parts = re.split(rf'(\b{word}\b)', run_text, flags=re.IGNORECASE)
            for part in parts:
                if part.lower() == word.lower():
                    new_run = para.add_run(translation)
                    new_run.bold = True
                    new_runs.append(new_run)
                elif part:
                    new_run = para.add_run(part)
                    new_run.bold = para.runs[i].bold
                    new_run.italic = para.runs[i].italic
                    new_run.underline = para.runs[i].underline
                    new_runs.append(new_run)
            i += 1
        para.clear()
        for new_run in new_runs:
            pass
    return doc


def process_file(file_path, num_words=200):
    """Processa o arquivo .docx especificado."""
    print(f"Lendo o arquivo: {file_path}")
    text = read_docx(file_path)

    print("Obtendo as palavras mais comuns...")
    top_words = get_top_words(text, num_words)

    print("Traduzindo palavras e substituindo no documento...")
    new_doc = docx.Document(file_path)
    translated_words = {}
    word_pairs = []

    for word, _ in tqdm(top_words, desc="Traduzindo palavras"):
        if is_valid_word(word):
            translation = translate_word(word)
            if translation:
                translated_words[word] = translation
                word_pairs.append((word, translation))
                new_doc = replace_word_in_doc(new_doc, word, translation)

    print("Gerando frases de exemplo...")
    example_sentences = generate_example_sentences(word_pairs)

    print("Adicionando palavras traduzidas e frases de exemplo ao documento...")
    translated_words_list = []
    for word, translation in translated_words.items():
        translated_words_list.append(f"{word} - {translation}")

    new_doc.add_paragraph("\nLista de palavras traduzidas:").bold = True
    for translated_word in translated_words_list:
        paragraph = new_doc.add_paragraph()
        word, translation = translated_word.split(" - ")
        paragraph.add_run(f"{word} - ").bold = False
        paragraph.add_run(f"{translation}").bold = True

        sentences = [s['sentence'] for s in example_sentences if s['pt_word'] == word]
        if sentences:
            for sentence in sentences:
                example_para = new_doc.add_paragraph()
                example_para.add_run("Example: ").italic = True
                example_para.add_run(sentence)

    new_file_name = 'docsx/ativo/Capitaes da Areia - Jorge Amado-A0.docx'
    new_doc.save(new_file_name)
    print(f"Processado: {file_path} -> {new_file_name}")


# Caminho do arquivo .docx a ser processado
file_path = 'docsx/ativo/Capitaes da Areia - Jorge Amado.docx'
num_words = 200  # Número de palavras mais comuns a serem obtidas

process_file(file_path, num_words)
print("Processo concluído.")
