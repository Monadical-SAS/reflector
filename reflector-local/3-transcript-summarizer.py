import argparse

import nltk

nltk.download('stopwords')
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize, sent_tokenize
from heapq import nlargest
from loguru import logger


# Function to initialize the argument parser
def init_argparse():
    parser = argparse.ArgumentParser(
        usage="%(prog)s <TRANSCRIPT> <SUMMARY>",
        description="Summarization"
    )
    parser.add_argument("transcript", type=str, default="transcript.txt", help="Path to the input transcript file")
    parser.add_argument("summary", type=str, default="summary.txt", help="Path to the output summary file")
    parser.add_argument("--num_sentences", type=int, default=5, help="Number of sentences to include in the summary")
    return parser


# Function to read the input transcript file
def read_transcript(file_path):
    with open(file_path, "r") as file:
        transcript = file.read()
    return transcript


# Function to preprocess the text by removing stop words and special characters
def preprocess_text(text):
    stop_words = set(stopwords.words('english'))
    words = word_tokenize(text)
    words = [w.lower() for w in words if w.isalpha() and w.lower() not in stop_words]
    return words


# Function to score each sentence based on the frequency of its words and return the top sentences
def summarize_text(text, num_sentences):
    # Tokenize the text into sentences
    sentences = sent_tokenize(text)

    # Preprocess the text by removing stop words and special characters
    words = preprocess_text(text)

    # Calculate the frequency of each word in the text
    word_freq = nltk.FreqDist(words)

    # Calculate the score for each sentence based on the frequency of its words
    sentence_scores = {}
    for i, sentence in enumerate(sentences):
        sentence_words = preprocess_text(sentence)
        for word in sentence_words:
            if word in word_freq:
                if i not in sentence_scores:
                    sentence_scores[i] = word_freq[word]
                else:
                    sentence_scores[i] += word_freq[word]

    # Select the top sentences based on their scores
    top_sentences = nlargest(num_sentences, sentence_scores, key=sentence_scores.get)

    # Sort the top sentences in the order they appeared in the original text
    summary_sent = sorted(top_sentences)
    summary = [sentences[i] for i in summary_sent]

    return " ".join(summary)


def main():
    # Initialize the argument parser and parse the arguments
    parser = init_argparse()
    args = parser.parse_args()

    # Read the input transcript file
    logger.info(f"Reading transcript from: {args.transcript}")
    transcript = read_transcript(args.transcript)

    # Summarize the transcript using the nltk library
    logger.info("Summarizing transcript")
    summary = summarize_text(transcript, args.num_sentences)

    # Write the summary to the output file
    logger.info(f"Writing summary to: {args.summary}")
    with open(args.summary, "w") as f:
        f.write("Summary of: " + args.transcript + "\n\n")
        f.write(summary)

    logger.info("Summarization completed")


if __name__ == "__main__":
    main()
