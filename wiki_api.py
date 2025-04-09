import requests
import csv
import re
import nltk
from collections import Counter
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator

# Ensure that NLTK's stopwords and punkt are downloaded
nltk.download('punkt')
nltk.download('stopwords')

# Function to fetch the full article content from Spanish Wikipedia API (no references)
def fetch_wikipedia_article(title):
    url = "https://es.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "format": "json",
        "titles": title,
        "prop": "extracts",  # Fetches the article text
        "exintro": False,  # This ensures you fetch the full article (not just the introduction)
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

# Function to process text and calculate word frequency (specifically for Spanish)
def process_text(text):
    # Clean the text
    cleaned_text = clean_text(text)

    # Tokenize the cleaned text
    words = word_tokenize(cleaned_text, language='spanish')

    # Remove stopwords (in Spanish)
    stop_words = set(stopwords.words('spanish'))
    words = [word for word in words if word not in stop_words]

    # Count the frequency of words
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

# Function to translate words from Spanish to English
def translate_words(word_list):
    translations = []
    for word in word_list:
        translated = GoogleTranslator(source='es', target='en').translate(word)
        translations.append([word, translated])

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