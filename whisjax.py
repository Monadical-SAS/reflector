#!/usr/bin/env python3

# summarize https://www.youtube.com/watch?v=imzTxoEDH_g --transcript=transcript.txt summary.txt
# summarize https://www.sprocket.org/video/cheesemaking.mp4 summary.txt
# summarize podcast.mp3 summary.txt

import argparse
import ast
import torch
import collections
import configparser
import jax.numpy as jnp
import matplotlib.pyplot as plt
import moviepy.editor
import moviepy.editor
import nltk
import os
import subprocess
import pandas as pd
import pickle
import re
import scattertext as st
import spacy
import tempfile
from loguru import logger
from pytube import YouTube
from transformers import BartTokenizer, BartForConditionalGeneration
from urllib.parse import urlparse
from whisper_jax import FlaxWhisperPipline
from wordcloud import WordCloud, STOPWORDS
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import TfidfVectorizer
from nltk.tokenize import word_tokenize
from sklearn.metrics.pairwise import cosine_similarity

from file_util import upload_files, download_files

nltk.download('punkt')
nltk.download('stopwords')

# Configurations can be found in config.ini. Set them properly before executing
config = configparser.ConfigParser()
config.read('config.ini')

WHISPER_MODEL_SIZE = config['DEFAULT']["WHISPER_MODEL_SIZE"]


def init_argparse() -> argparse.ArgumentParser:
    """
    Parse the CLI arguments
    :return: parser object
    """
    parser = argparse.ArgumentParser(
        usage="%(prog)s [OPTIONS] <LOCATION> <OUTPUT>",
        description="Creates a transcript of a video or audio file, then summarizes it using ChatGPT."
    )

    parser.add_argument("-l", "--language", help="Language that the summary should be written in", type=str,
                        default="english", choices=['english', 'spanish', 'french', 'german', 'romanian'])
    parser.add_argument("-t", "--transcript", help="Save a copy of the intermediary transcript file", type=str)
    parser.add_argument("location")
    parser.add_argument("output")

    return parser


def chunk_text(txt, max_chunk_length=int(config["DEFAULT"]["MAX_CHUNK_LENGTH"])):
    """
    Split text into smaller chunks.
    :param txt: Text to be chunked
    :param max_chunk_length: length of chunk
    :return: chunked texts
    """
    sentences = nltk.sent_tokenize(txt)
    chunks = []
    current_chunk = ""
    for sentence in sentences:
        if len(current_chunk) + len(sentence) < max_chunk_length:
            current_chunk += f" {sentence.strip()}"
        else:
            chunks.append(current_chunk.strip())
            current_chunk = f"{sentence.strip()}"
    chunks.append(current_chunk.strip())
    return chunks


def summarize_chunks(chunks, tokenizer, model):
    """
    Summarize each chunk using a summarizer model
    :param chunks:
    :param tokenizer:
    :param model:
    :return:
    """
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    summaries = []
    for c in chunks:
        input_ids = tokenizer.encode(c, return_tensors='pt')
        input_ids = input_ids.to(device)
        with torch.no_grad():
            summary_ids = model.generate(input_ids,
                               num_beams=int(config["DEFAULT"]["BEAM_SIZE"]), length_penalty=2.0,
                               max_length=int(config["DEFAULT"]["MAX_LENGTH"]), early_stopping=True)
            summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
            summaries.append(summary)
    return summaries


def create_wordcloud():
    """
    Create a basic word cloud visualization of transcribed text
    :return: None. The wordcloud image is saved locally
    """
    with open("transcript.txt", "r") as f:
        transcription_text = f.read()

    stopwords = set(STOPWORDS)

    # python_mask = np.array(PIL.Image.open("download1.png"))

    wordcloud = WordCloud(height=800, width=800,
                          background_color='white',
                          stopwords=stopwords,
                          min_font_size=8).generate(transcription_text)

    # Plot wordcloud and save image
    plt.figure(facecolor=None)
    plt.imshow(wordcloud, interpolation="bilinear")
    plt.axis("off")
    plt.tight_layout(pad=0)
    plt.savefig("wordcloud.png")


def create_talk_diff_scatter_viz():
    """
    Perform agenda vs transription diff to see covered topics.
    Create a scatter plot of words in topics.
    :return: None. Saved locally.
    """
    spaCy_model = "en_core_web_md"
    nlp = spacy.load(spaCy_model)
    nlp.add_pipe('sentencizer')

    agenda_topics = []
    agenda = []
    # Load the agenda
    with open("agenda-headers.txt", "r") as f:
        for line in f.readlines():
            if line.strip():
                agenda.append(line.strip())
                agenda_topics.append(line.split(":")[0])

    # Load the transcription with timestamp
    with open("transcript_timestamps.txt", "r") as f:
        transcription_timestamp_text = f.read()

    res = ast.literal_eval(transcription_timestamp_text)
    chunks = res["chunks"]

    # create df for processing
    df = pd.DataFrame.from_dict(res["chunks"])

    covered_items = {}
    # ts: timestamp
    # Map each timestamped chunk with top1 and top2 matched agenda
    ts_to_topic_mapping_top_1 = {}
    ts_to_topic_mapping_top_2 = {}

    # Also create a mapping of the different timestamps in which each topic was covered
    topic_to_ts_mapping_top_1 = collections.defaultdict(list)
    topic_to_ts_mapping_top_2 = collections.defaultdict(list)

    similarity_threshold = 0.7

    for c in chunks:
        doc_transcription = nlp(c["text"])
        topic_similarities = []
        for item in range(len(agenda)):
            item_doc = nlp(agenda[item])
            # if not doc_transcription or not all(token.has_vector for token in doc_transcription):
            if not doc_transcription:
                continue
            similarity = doc_transcription.similarity(item_doc)
            topic_similarities.append((item, similarity))
        topic_similarities.sort(key=lambda x: x[1], reverse=True)
        for i in range(2):
            if topic_similarities[i][1] >= similarity_threshold:
                covered_items[agenda[topic_similarities[i][0]]] = True
            # top1 match
            if i == 0:
                ts_to_topic_mapping_top_1[c["timestamp"]] = agenda_topics[topic_similarities[i][0]]
                topic_to_ts_mapping_top_1[agenda_topics[topic_similarities[i][0]]].append(c["timestamp"])
            # top2 match
            else:
                ts_to_topic_mapping_top_2[c["timestamp"]] = agenda_topics[topic_similarities[i][0]]
                topic_to_ts_mapping_top_2[agenda_topics[topic_similarities[i][0]]].append(c["timestamp"])

    def create_new_columns(record):
        """
        Accumulate the mapping information into the df
        :param record:
        :return:
        """
        record["ts_to_topic_mapping_top_1"] = ts_to_topic_mapping_top_1[record["timestamp"]]
        record["ts_to_topic_mapping_top_2"] = ts_to_topic_mapping_top_2[record["timestamp"]]
        return record

    df = df.apply(create_new_columns, axis=1)

    # Count the number of items covered and calculatre the percentage
    num_covered_items = sum(covered_items.values())
    percentage_covered = num_covered_items / len(agenda) * 100

    # Print the results
    print("💬 Agenda items covered in the transcription:")
    for item in agenda:
        if item in covered_items and covered_items[item]:
            print("✅ ", item)
        else:
            print("❌ ", item)
    print("📊 Coverage: {:.2f}%".format(percentage_covered))

    # Save df, mappings for further experimentation
    df.to_pickle("df.pkl")

    my_mappings = [ts_to_topic_mapping_top_1, ts_to_topic_mapping_top_2,
                   topic_to_ts_mapping_top_1, topic_to_ts_mapping_top_2]
    pickle.dump(my_mappings, open("mappings.pkl", "wb"))

    # to load,  my_mappings = pickle.load( open ("mappings.pkl", "rb") )

    # pick the 2 most matched topic to be used for plotting
    topic_times = collections.defaultdict(int)
    for key in ts_to_topic_mapping_top_1.keys():
        if key[0] is None or key[1] is None:
            continue
        duration = key[1] - key[0]
        topic_times[ts_to_topic_mapping_top_1[key]] += duration

    topic_times = sorted(topic_times.items(), key=lambda x: x[1], reverse=True)

    cat_1 = topic_times[0][0]
    cat_1_name = topic_times[0][0]
    cat_2_name = topic_times[1][0]

    # Scatter plot of topics
    df = df.assign(parse=lambda df: df.text.apply(st.whitespace_nlp_with_sentences))
    corpus = st.CorpusFromParsedDocuments(
        df, category_col='ts_to_topic_mapping_top_1', parsed_col='parse'
    ).build().get_unigram_corpus().compact(st.AssociationCompactor(2000))
    html = st.produce_scattertext_explorer(
        corpus,
        category=cat_1,
        category_name=cat_1_name,
        not_category_name=cat_2_name,
        minimum_term_frequency=0, pmi_threshold_coefficient=0,
        width_in_pixels=1000,
        transform=st.Scalers.dense_rank
    )
    open('./demo_compact.html', 'w').write(html)

def preprocess_sentence(sentence):
    stop_words = set(stopwords.words('english'))
    tokens = word_tokenize(sentence.lower())
    tokens = [token for token in tokens if token.isalnum() and token not in stop_words]
    return ' '.join(tokens)

def compute_similarity(sent1, sent2):
    tfidf_vectorizer = TfidfVectorizer()
    tfidf_matrix = tfidf_vectorizer.fit_transform([sent1, sent2])
    return cosine_similarity(tfidf_matrix[0], tfidf_matrix[1])[0][0]

def remove_almost_alike_sentences(sentences, threshold=0.7):
    num_sentences = len(sentences)
    removed_indices = set()

    for i in range(num_sentences):
        if i not in removed_indices:
            for j in range(i + 1, num_sentences):
                if j not in removed_indices:
                    sentence1 = preprocess_sentence(sentences[i])
                    sentence2 = preprocess_sentence(sentences[j])
                    similarity = compute_similarity(sentence1, sentence2)

                    if similarity >= threshold:
                        removed_indices.add(max(i, j))

    filtered_sentences = [sentences[i] for i in range(num_sentences) if i not in removed_indices]
    return filtered_sentences

def remove_outright_duplicate_sentences_from_chunk(chunk):
    chunk_text = chunk["text"]
    sentences = nltk.sent_tokenize(chunk_text)
    nonduplicate_sentences = list(dict.fromkeys(sentences))
    return nonduplicate_sentences

def remove_whisper_repititive_hallucination(nonduplicate_sentences):
    chunk_sentences = []

    for sent in nonduplicate_sentences:
        temp_result = ""
        seen = {}
        words = nltk.word_tokenize(sent)
        n_gram_filter = 3
        for i in range(len(words)):
            if str(words[i:i + n_gram_filter]) in seen and seen[str(words[i:i + n_gram_filter])] == words[
                                                                                                    i + 1:i + n_gram_filter + 2]:
                pass
            else:
                seen[str(words[i:i + n_gram_filter])] = words[i + 1:i + n_gram_filter + 2]
                temp_result += words[i]
                temp_result += " "
        chunk_sentences.append(temp_result)
    return chunk_sentences

def remove_duplicates_from_transcript_chunk(whisper_result):
    for chunk in whisper_result["chunks"]:
        nonduplicate_sentences = remove_outright_duplicate_sentences_from_chunk(chunk)
        chunk_sentences = remove_whisper_repititive_hallucination(nonduplicate_sentences)
        similarity_matched_sentences = remove_almost_alike_sentences(chunk_sentences)
        chunk["text"] = " ".join(similarity_matched_sentences)
    return whisper_result

def summarize(transcript_text, output_file,
              summarize_using_chunks=config["DEFAULT"]["SUMMARIZE_USING_CHUNKS"]):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    summary_model = config["DEFAULT"]["SUMMARY_MODEL"]
    if not summary_model:
        summary_model = "facebook/bart-large-cnn"

    # Summarize the generated transcript using the BART model
    logger.info(f"Loading BART model: {summary_model}")
    tokenizer = BartTokenizer.from_pretrained(summary_model)
    model = BartForConditionalGeneration.from_pretrained(summary_model)
    model = model.to(device)

    if summarize_using_chunks != "YES":
        inputs = tokenizer.batch_encode_plus([transcript_text], truncation=True, padding='longest',
                                             max_length=int(config["DEFAULT"]["INPUT_ENCODING_MAX_LENGTH"]),
                                             return_tensors='pt')
        inputs = inputs.to(device)

        with torch.no_grad():
            summaries = model.generate(inputs['input_ids'],
                                       num_beams=int(config["DEFAULT"]["BEAM_SIZE"]), length_penalty=2.0,
                                       max_length=int(config["DEFAULT"]["MAX_LENGTH"]), early_stopping=True)

        decoded_summaries = [tokenizer.decode(summary, skip_special_tokens=True, clean_up_tokenization_spaces=False) for
                             summary in summaries]
        summary = " ".join(decoded_summaries)
        with open(output_file, 'w') as f:
            f.write(summary.strip() + "\n\n")
    else:
        logger.info("Breaking transcript into smaller chunks")
        chunks = chunk_text(transcript_text)

        logger.info(f"Transcript broken into {len(chunks)} chunks of at most 500 words")  # TODO fix variable

        logger.info(f"Writing summary text to: {output_file}")
        with open(output_file, 'w') as f:
            summaries = summarize_chunks(chunks, tokenizer, model)
            for summary in summaries:
                f.write(summary.strip() + " ")

def main():
    parser = init_argparse()
    args = parser.parse_args()

    # Parse the location string that was given to us, and figure out if it's a
    # local file (audio or video), a YouTube URL, or a URL referencing an
    # audio or video file.
    url = urlparse(args.location)

    # S3 : Pull artefacts to S3 bucket ?

    media_file = ""
    if url.scheme == 'http' or url.scheme == 'https':
        # Check if we're being asked to retreive a YouTube URL, which is handled
        # diffrently, as we'll use a secondary site to download the video first.
        if re.search('youtube.com', url.netloc, re.IGNORECASE):
            # Download the lowest resolution YouTube video (since we're just interested in the audio).
            # It will be saved to the current directory.
            logger.info("Downloading YouTube video at url: " + args.location)

            youtube = YouTube(args.location)
            media_file = youtube.streams.filter(progressive=True, file_extension='mp4').order_by(
                'resolution').asc().first().download()

            logger.info("Saved downloaded YouTube video to: " + media_file)
        else:
            # XXX - Download file using urllib, check if file is audio/video using python-magic
            logger.info(f"Downloading file at url: {args.location}")
            logger.info("  XXX - This method hasn't been implemented yet.")
    elif url.scheme == '':
        media_file = url.path
        # If file is not present locally, take it from S3 bucket
        if not os.path.exists(media_file):
            download_files([media_file])

        if media_file.endswith(".m4a"):
            subprocess.run(["ffmpeg", "-i", media_file, f"{media_file}.mp4"])
            input_file = f"{media_file}.mp4"
    else:
        print("Unsupported URL scheme: " + url.scheme)
        quit()

    # Handle video
    try:
        video = moviepy.editor.VideoFileClip(media_file)
        audio_filename = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False).name
        video.audio.write_audiofile(audio_filename, logger=None)
        logger.info(f"Extracting audio to: {audio_filename}")
    # Handle audio only file
    except:
        audio = moviepy.editor.AudioFileClip(media_file)
        audio_filename = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False).name
        audio.write_audiofile(audio_filename, logger=None)

    logger.info("Finished extracting audio")

    # Convert the audio to text using the OpenAI Whisper model
    pipeline = FlaxWhisperPipline("openai/whisper-" + WHISPER_MODEL_SIZE,
                                  dtype=jnp.float16,
                                  batch_size=16)
    whisper_result = pipeline(audio_filename, return_timestamps=True)
    logger.info("Finished transcribing file")

    whisper_result = remove_duplicates_from_transcript_chunk(whisper_result)

    transcript_text = ""
    for chunk in whisper_result["chunks"]:
        transcript_text += chunk["text"]

    # If we got the transcript parameter on the command line,
    # save the transcript to the specified file.
    if args.transcript:
        logger.info(f"Saving transcript to: {args.transcript}")
        transcript_file = open(args.transcript, "w")
        transcript_file_timestamps = open(args.transcript[0:len(args.transcript) - 4] + "_timestamps.txt", "w")
        transcript_file.write(transcript_text)
        transcript_file_timestamps.write(str(whisper_result))
        transcript_file.close()
        transcript_file_timestamps.close()

    logger.info("Creating word cloud")
    create_wordcloud()

    logger.info("Performing talk-diff and talk-diff visualization")
    create_talk_diff_scatter_viz()

    # S3 : Push artefacts to S3 bucket
    files_to_upload = ["transcript.txt", "transcript_timestamps.txt",
                       "df.pkl",
                       "wordcloud.png", "mappings.pkl"]
    upload_files(files_to_upload)

    summarize(transcript_text, args.output)

    logger.info("Summarization completed")

    # Summarization takes a lot of time, so do this separately at the end
    files_to_upload = ["summary.txt"]
    upload_files(files_to_upload)


if __name__ == "__main__":
    main()
