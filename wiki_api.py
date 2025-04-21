import requests
import csv
import re
import nltk
import time
from collections import Counter
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator

# Ensure that NLTK's stopwords and punkt are downloaded
nltk.download('punkt')
nltk.download('stopwords')

# Function to fetch the full article content from Wikipedia API (no references)
def fetch_wikipedia_article(title, lang_code='es'):
    url = f"https://{lang_code}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "format": "json",
        "titles": title,
        "prop": "extracts",
        "exintro": False,
    }
    response = requests.get(url, params=params)
    data = response.json()
    page = list(data['query']['pages'].values())[0]
    extract = page.get('extract', "")
    return extract

# Function to clean and process text (removes HTML tags and non-alphanumeric characters)
def clean_text(text):
    # Use BeautifulSoup to remove HTML tags
    text = BeautifulSoup(text, "html.parser").get_text()

    # Remove non-alphanumeric characters (except for accented characters)
    text = re.sub(r'[^a-zA-Záéíóúüñ\s]', '', text.lower())

    # Further clean up any excessive whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    return text

# Function to remove references from the article content
def remove_references(text):
    # Use BeautifulSoup to parse the HTML and remove <ref> tags
    soup = BeautifulSoup(text, "html.parser")

    # Remove all <ref> and <sup> tags (commonly used for citations and references)
    for ref_tag in soup.find_all(['ref', 'sup']):
        ref_tag.decompose()  # Decomposing removes the tag and its contents

    return str(soup)

# Function to process text and calculate word frequency
def process_text(text, lang_code='es'):
    # Clean the text
    cleaned_text = clean_text(text)

    # Map Wikipedia language codes to NLTK language names
    lang_map = {
        'es': 'spanish',
        'fr': 'french',
        'de': 'german',
        'it': 'italian',
        'pt': 'portuguese'
    }

    # Get NLTK language name or fall back to English
    nltk_lang = lang_map.get(lang_code, 'english')

    # Load sentence tokenizer for the language
    try:
        sentence_tokenizer = nltk.data.load(f'tokenizers/punkt/{nltk_lang}.pickle')
    except LookupError:
        print(f"Tokenizer for '{nltk_lang}' not found. Downloading punkt again.")
        nltk.download('punkt', force=True)
        sentence_tokenizer = nltk.data.load(f'tokenizers/punkt/{nltk_lang}.pickle')

    # Tokenize into sentences, then words
    sentences = sentence_tokenizer.tokenize(cleaned_text)
    words = []
    for sentence in sentences:
        words.extend(word_tokenize(sentence))

    # Load stopwords for the language
    try:
        stop_words = set(stopwords.words(nltk_lang))
    except OSError:
        print(f"Stopwords for '{nltk_lang}' not found. Using empty set.")
        stop_words = set()

    # Filter out stopwords and count word frequency
    words = [word for word in words if word not in stop_words]
    word_freq = Counter(words)

    return word_freq

# Function to save results to CSV (top 100 words and their frequency)
def save_to_csv(word_freq, filename='top_100_words.csv'):
    # Get the top 100 words
    top_words = word_freq.most_common(100)

    # Write to CSV
    with open(filename, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['Word', 'Frequency'])
        writer.writerows(top_words)

    print(f"Top 100 words saved to {filename}")

# Function to translate words to English
def translate_words(word_list, source_lang='es', target_lang='en'):
    translations = []
    for word in word_list:
        try:
            translated = GoogleTranslator(source=source_lang, target=target_lang).translate(word)
            translations.append([word, translated])
            time.sleep(0.5)
        except Exception as e:
            print(f"Error translating {word}: {e}")
            translations.append([word, ""])
    return translations


# Function to save translated words to CSV
def save_translated_words(translations, filename='translated_words.csv'):
    # Write to CSV (without frequency)
    with open(filename, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['Spanish Word', 'English Translation'])
        writer.writerows(translations)

    print(f"Translated words saved to {filename}")

# Main function
def main():
    # Get the article URL (Spanish Wikipedia articles only)
    article_url = input("Enter the Wikipedia article URL (must be in Spanish): ")

    # Extract the article title from the URL
    article_title = article_url.split('/')[-1]

    # Fetch the full article content in Spanish
    article_content = fetch_wikipedia_article(article_title)

    if article_content:
        # Remove references (like <ref> tags) from the content
        clean_article = remove_references(article_content)

        # Process the cleaned text and get word frequencies
        word_freq = process_text(clean_article)

        # Save the results to CSV (top 100 words)
        save_to_csv(word_freq)

        # Get the top 100 words (just the words, without frequency)
        top_100_words = [word for word, _ in word_freq.most_common(100)]

        # Translate the words to English
        translations = translate_words(top_100_words)

        # Save the translated words to CSV
        save_translated_words(translations)

    else:
        print("No content found for the given article.")

if __name__ == "__main__":
    main()