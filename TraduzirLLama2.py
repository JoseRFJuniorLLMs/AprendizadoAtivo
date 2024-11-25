import docx
from collections import Counter
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import re
import torch
from transformers import LlamaTokenizer, LlamaForCausalLM
from googletrans import Translator
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TranslationCache:
    def __init__(self, cache_file: str = "translation_cache.json"):
        """Initialize translation cache with file persistence."""
        self.cache_file = cache_file
        self.cache = self._load_cache()

    def _load_cache(self) -> Dict:
        """Load cache from file if it exists."""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                logger.warning(f"Cache file corrupted, creating new cache")
                return {}
        return {}

    def save_cache(self):
        """Save cache to file."""
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=2)

    def get(self, key: str) -> Optional[Dict]:
        """Get cached translation and examples if they exist."""
        return self.cache.get(key)

    def add(self, key: str, translation: str, example: str, style: str):
        """Add new translation and example to cache."""
        self.cache[key] = {
            'translation': translation,
            'example': example,
            'style': style,
            'timestamp': datetime.now().isoformat()
        }
        self.save_cache()

class LlamaProcessor:
    def __init__(self, model_path: str):
        """Initialize Llama model with improved configuration."""
        logger.info("Initializing Llama model...")
        self.tokenizer = LlamaTokenizer.from_pretrained(model_path)
        self.model = LlamaForCausalLM.from_pretrained(
            model_path,
            torch_dtype=torch.float16,
            device_map="auto",
            load_in_8bit=True  # Enable 8-bit quantization for memory efficiency
        )
        self.model.eval()

        # Define sentence style templates
        self.style_prompts = {
            'formal': "Generate a formal and professional English sentence using",
            'informal': "Write a casual, everyday English sentence using",
            'academic': "Create an academic or technical English sentence using",
            'business': "Write a business-context English sentence using",
            'creative': "Create a creative and engaging English sentence using"
        }

    def generate_sentence(self, word: str, style: str = 'formal', max_attempts: int = 3) -> Tuple[str, bool]:
        """Generate a sentence using the given word with style and quality control."""
        style_prompt = self.style_prompts.get(style, self.style_prompts['formal'])
        prompt = f"{style_prompt} the word '{word}'"

        for attempt in range(max_attempts):
            try:
                inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)

                with torch.no_grad():
                    outputs = self.model.generate(
                        inputs['input_ids'],
                        max_length=50,
                        num_return_sequences=1,
                        temperature=0.7,
                        do_sample=True,
                        pad_token_id=self.tokenizer.eos_token_id
                    )

                sentence = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
                clean_sentence = self._clean_generated_sentence(sentence, word)

                if self._validate_sentence(clean_sentence, word):
                    return clean_sentence, True

            except Exception as e:
                logger.error(f"Error generating sentence (attempt {attempt + 1}): {e}")

        return f"Example with '{word}'", False

    def _clean_generated_sentence(self, sentence: str, word: str) -> str:
        """Clean and format the generated sentence."""
        # Remove the prompt and any extra whitespace
        if "using the word" in sentence.lower():
            sentence = sentence.split("using the word")[-1]
        return sentence.strip()

    def _validate_sentence(self, sentence: str, word: str) -> bool:
        """Validate the quality of generated sentence."""
        if not sentence or len(sentence) < 10:
            return False
        if word.lower() not in sentence.lower():
            return False
        if sentence.count('.') > 2:  # Avoid multiple sentences
            return False
        return True

class DocumentProcessor:
    def __init__(self, llama_model_path: str):
        """Initialize document processor with enhanced features."""
        self.llama = LlamaProcessor(llama_model_path)
        self.translator = Translator()
        self.cache = TranslationCache()
        self.processed_words = {}

    def process_run_content(self, run, word: str, translation: str, example: str) -> None:
        """Process content within a run, handling split words correctly."""
        text = run.text
        pattern = rf'\b{re.escape(word)}\b'

        # Check if the word is split across runs
        if not re.search(pattern, text, re.IGNORECASE):
            return

        replacement = f"{translation} ({example})"
        run.text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        run.bold = True

    def process_file(self,
                    input_file_path: str,
                    output_file_path: str,
                    num_words: int = 200,
                    style: str = 'formal') -> Dict:
        """Process the document with enhanced features and error handling."""
        logger.info(f"Starting processing of file: {input_file_path}")

        try:
            doc = docx.Document(input_file_path)
            text = ' '.join(para.text for para in doc.paragraphs)

            # Get top words
            tokens = word_tokenize(text.lower())
            stop_words = set(stopwords.words('portuguese'))
            valid_tokens = [word for word in tokens
                          if self._is_valid_word(word) and word not in stop_words]
            top_words = Counter(valid_tokens).most_common(num_words)

            new_doc = docx.Document(input_file_path)

            # Process each word
            for word, count in top_words:
                cached_data = self.cache.get(word)

                if cached_data and cached_data['style'] == style:
                    translation = cached_data['translation']
                    example = cached_data['example']
                    logger.info(f"Using cached translation for: {word}")
                else:
                    try:
                        translation = self.translator.translate(
                            word, src='pt', dest='en'
                        ).text
                        example, is_valid = self.llama.generate_sentence(
                            translation, style
                        )

                        if is_valid:
                            self.cache.add(word, translation, example, style)
                        else:
                            logger.warning(
                                f"Could not generate valid sentence for: {word}"
                            )
                            continue

                    except Exception as e:
                        logger.error(f"Error processing word '{word}': {e}")
                        continue

                self.processed_words[word] = {
                    'translation': translation,
                    'example': example,
                    'style': style
                }

                # Process document content
                for para in new_doc.paragraphs:
                    for run in para.runs:
                        self.process_run_content(
                            run, word, translation, example
                        )

            # Add processed words section
            self._add_processed_words_section(new_doc)

            # Save document
            new_doc.save(output_file_path)
            logger.info(f"Successfully saved processed document to: {output_file_path}")

            return self.processed_words

        except Exception as e:
            logger.error(f"Error processing document: {e}")
            raise

    def _is_valid_word(self, word: str) -> bool:
        """Check if word is valid for processing."""
        return bool(re.match(r'^[A-Za-zÀ-ÿ0-9]+$', word)) and len(word) > 1

    def _add_processed_words_section(self, doc) -> None:
        """Add processed words section to document."""
        doc.add_paragraph("\nProcessed Words Dictionary:")
        for word, info in self.processed_words.items():
            doc.add_paragraph(
                f"{word} - {info['translation']}\n"
                f"Example ({info['style']}): {info['example']}"
            )

def main():
    # Configuration
    config = {
        'llama_model_path': "path/to/llama-3.2-model",
        'input_file': "docsx/ativo/O Pequeno Principe - Antoine de Saint-Exupery.docx",
        'output_file': "docsx/ativo/O Pequeno Principe - Antoine de Saint-Exupery-A0.docx",
        'num_words': 200,
        'style': 'formal'  # Options: formal, informal, academic, business, creative
    }

    try:
        processor = DocumentProcessor(config['llama_model_path'])
        processed_words = processor.process_file(
            config['input_file'],
            config['output_file'],
            config['num_words'],
            config['style']
        )

        logger.info(f"Successfully processed {len(processed_words)} words")

    except Exception as e:
        logger.error(f"Failed to process document: {e}")
        raise

if __name__ == "__main__":
    main()