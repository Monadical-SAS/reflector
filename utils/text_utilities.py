import nltk
import torch
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from transformers import BartForConditionalGeneration, BartTokenizer

from log_utils import logger
from run_utils import config

nltk.download('punkt', quiet=True)


def preprocess_sentence(sentence):
    stop_words = set(stopwords.words('english'))
    tokens = word_tokenize(sentence.lower())
    tokens = [token for token in tokens
              if token.isalnum() and token not in stop_words]
    return ' '.join(tokens)


def compute_similarity(sent1, sent2):
    """
    Compute the similarity
    """
    tfidf_vectorizer = TfidfVectorizer()
    if sent1 is not None and sent2 is not None:
        tfidf_matrix = tfidf_vectorizer.fit_transform([sent1, sent2])
        return cosine_similarity(tfidf_matrix[0], tfidf_matrix[1])[0][0]
    return 0.0


def remove_almost_alike_sentences(sentences, threshold=0.7):
    num_sentences = len(sentences)
    removed_indices = set()

    for i in range(num_sentences):
        if i not in removed_indices:
            for j in range(i + 1, num_sentences):
                if j not in removed_indices:
                    l_i = len(sentences[i])
                    l_j = len(sentences[j])
                    if l_i == 0 or l_j == 0:
                        if l_i == 0:
                            removed_indices.add(i)
                        if l_j == 0:
                            removed_indices.add(j)
                    else:
                        sentence1 = preprocess_sentence(sentences[i])
                        sentence2 = preprocess_sentence(sentences[j])
                        if len(sentence1) != 0 and len(sentence2) != 0:
                            similarity = compute_similarity(sentence1,
                                                            sentence2)

                            if similarity >= threshold:
                                removed_indices.add(max(i, j))

    filtered_sentences = [sentences[i] for i in range(num_sentences)
                          if i not in removed_indices]
    return filtered_sentences


def remove_outright_duplicate_sentences_from_chunk(chunk):
    chunk_text = chunk["text"]
    sentences = nltk.sent_tokenize(chunk_text)
    nonduplicate_sentences = list(dict.fromkeys(sentences))
    return nonduplicate_sentences


def remove_whisper_repetitive_hallucination(nonduplicate_sentences):
    chunk_sentences = []

    for sent in nonduplicate_sentences:
        temp_result = ""
        seen = {}
        words = nltk.word_tokenize(sent)
        n_gram_filter = 3
        for i in range(len(words)):
            if str(words[i:i + n_gram_filter]) in seen and \
                    seen[str(words[i:i + n_gram_filter])] == \
                    words[i + 1:i + n_gram_filter + 2]:
                pass
            else:
                seen[str(words[i:i + n_gram_filter])] = \
                    words[i + 1:i + n_gram_filter + 2]
                temp_result += words[i]
                temp_result += " "
        chunk_sentences.append(temp_result)
    return chunk_sentences


def post_process_transcription(whisper_result):
    transcript_text = ""
    for chunk in whisper_result["chunks"]:
        nonduplicate_sentences = \
            remove_outright_duplicate_sentences_from_chunk(chunk)
        chunk_sentences = \
            remove_whisper_repetitive_hallucination(nonduplicate_sentences)
        similarity_matched_sentences = \
            remove_almost_alike_sentences(chunk_sentences)
        chunk["text"] = " ".join(similarity_matched_sentences)
        transcript_text += chunk["text"]
    whisper_result["text"] = transcript_text
    return whisper_result


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
            summary_ids = \
                model.generate(input_ids,
                               num_beams=int(config["DEFAULT"]["BEAM_SIZE"]),
                               length_penalty=2.0,
                               max_length=int(config["DEFAULT"]["MAX_LENGTH"]),
                               early_stopping=True)
            summary = tokenizer.decode(summary_ids[0],
                                       skip_special_tokens=True)
            summaries.append(summary)
    return summaries


def chunk_text(text,
               max_chunk_length=int(config["DEFAULT"]["MAX_CHUNK_LENGTH"])):
    """
    Split text into smaller chunks.
    :param text: Text to be chunked
    :param max_chunk_length: length of chunk
    :return: chunked texts
    """
    sentences = nltk.sent_tokenize(text)
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


def summarize(transcript_text, timestamp,
              real_time=False,
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

    output_filename = "summary_" + timestamp.strftime("%m-%d-%Y_%H:%M:%S") + ".txt"
    if real_time:
        output_filename = "real_time_" + output_filename

    if summarize_using_chunks != "YES":
        inputs = tokenizer. \
            batch_encode_plus([transcript_text], truncation=True,
                              padding='longest',
                              max_length=int(config["DEFAULT"]["INPUT_ENCODING_MAX_LENGTH"]),
                              return_tensors='pt')
        inputs = inputs.to(device)

        with torch.no_grad():
            summaries = model.generate(inputs['input_ids'],
                                       num_beams=int(config["DEFAULT"]["BEAM_SIZE"]), length_penalty=2.0,
                                       max_length=int(config["DEFAULT"]["MAX_LENGTH"]), early_stopping=True)

        decoded_summaries = [tokenizer.decode(summary, skip_special_tokens=True, clean_up_tokenization_spaces=False)
                             for summary in summaries]
        summary = " ".join(decoded_summaries)
        with open("./artefacts/" + output_filename, 'w') as f:
            f.write(summary.strip() + "\n")
    else:
        logger.info("Breaking transcript into smaller chunks")
        chunks = chunk_text(transcript_text)

        logger.info(f"Transcript broken into {len(chunks)} "
                    f"chunks of at most 500 words")

        logger.info(f"Writing summary text to: {output_filename}")
        with open(output_filename, 'w') as f:
            summaries = summarize_chunks(chunks, tokenizer, model)
            for summary in summaries:
                f.write(summary.strip() + " ")
