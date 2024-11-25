import docx
from collections import Counter
from googletrans import Translator
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import re
import torch
from transformers import LlamaTokenizer, LlamaForCausalLM

# Download required NLTK resources
nltk.download('punkt', quiet=True)
nltk.download('stopwords', quiet=True)


class LlamaProcessor:
    def __init__(self, model_path):
        """Initialize Llama model and tokenizer."""
        self.tokenizer = LlamaTokenizer.from_pretrained(model_path)
        self.model = LlamaForCausalLM.from_pretrained(
            model_path,
            torch_dtype=torch.float16,
            device_map="auto"
        )
        self.model.eval()

    def generate_sentence(self, word, max_length=50):
        """Generate a sentence using the given word."""
        prompt = f"Generate a simple example sentence in English using the word '{word}'"
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)

        with torch.no_grad():
            outputs = self.model.generate(
                inputs['input_ids'],
                max_length=max_length,
                num_return_sequences=1,
                temperature=0.7,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id
            )

        sentence = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        # Extract only the generated sentence, removing the prompt
        return sentence.split("using the word")[1].strip()


class DocumentProcessor:
    def __init__(self, llama_model_path):
        """Initialize the document processor with Llama model."""
        self.llama = LlamaProcessor(llama_model_path)
        self.translator = Translator()

    def read_docx(self, file_path):
        """Read the .docx file and return the complete text."""
        doc = docx.Document(file_path)
        return ' '.join(para.text for para in doc.paragraphs)

    def is_valid_word(self, word):
        """Check if the word is valid (only alphanumeric and no special characters)."""
        return bool(re.match(r'^[A-Za-zÀ-ÿ0-9]+$', word))

    def get_top_words(self, text, n=100):
        """Get the n most common words from the text, excluding stopwords."""
        tokens = word_tokenize(text.lower())
        stop_words = set(stopwords.words('portuguese'))
        tokens = [word for word in tokens if self.is_valid_word(word) and word not in stop_words]
        return Counter(tokens).most_common(n)

    def translate_word(self, word):
        """Translate a single word using Google Translate."""
        try:
            return self.translator.translate(word, src='pt', dest='en').text
        except Exception as e:
            print(f"Error translating '{word}': {e}")
            return None

    def replace_word_in_doc(self, doc, word, translation, example_sentence):
        """Replace the word in the document with its English translation and example sentence."""
        for para in doc.paragraphs:
            for run in para.runs:
                if word.lower() in run.text.lower():
                    replacement = f"{translation} ({example_sentence})"
                    run.text = re.sub(
                        rf'\b{word}\b',
                        replacement,
                        run.text,
                        flags=re.IGNORECASE
                    )
                    run.bold = True
        return doc

    def process_file(self, input_file_path, output_file_path, num_words=200):
        """Process the specified .docx file with Llama integration."""
        print(f"Processing file: {input_file_path}")

        # Read the document
        text = self.read_docx(input_file_path)

        # Get the most common words
        top_words = self.get_top_words(text, num_words)

        # Create new document
        new_doc = docx.Document(input_file_path)

        # Dictionary to store translations and examples
        processed_words = {}

        # Process each word
        for word, count in top_words:
            if self.is_valid_word(word):
                # Get translation
                translation = self.translate_word(word)
                if translation:
                    try:
                        # Generate example sentence using Llama
                        example_sentence = self.llama.generate_sentence(translation)
                        processed_words[word] = {
                            'translation': translation,
                            'example': example_sentence
                        }
                        # Replace in document
                        new_doc = self.replace_word_in_doc(
                            new_doc,
                            word,
                            translation,
                            example_sentence
                        )
                        print(f"Processed: {word} -> {translation}")
                    except Exception as e:
                        print(f"Error processing '{word}': {e}")

        # Add translated words section
        new_doc.add_paragraph("\nProcessed Words Dictionary:")
        for word, info in processed_words.items():
            new_doc.add_paragraph(
                f"{word} - {info['translation']}\n"
                f"Example: {info['example']}"
            )

        # Save the new document
        new_doc.save(output_file_path)
        print(f"Saved processed document to: {output_file_path}")
        return processed_words


def main():
    # Configuration
    llama_model_path = "path/to/llama-3.2-model"  # Replace with actual model path
    input_file = "docsx/ativo/O Pequeno Principe - Antoine de Saint-Exupery-A0.docx"
    output_file = "docsx/ativo/O Pequeno Principe - Antoine de Saint-Exupery.docx"
    num_words = 200

    # Initialize and run processor
    processor = DocumentProcessor(llama_model_path)

    try:
        processed_words = processor.process_file(
            input_file,
            output_file,
            num_words
        )
        print("Processing completed successfully!")

        # Print summary
        print(f"\nProcessed {len(processed_words)} words")

    except Exception as e:
        print(f"An error occurred during processing: {e}")


if __name__ == "__main__":
    main()