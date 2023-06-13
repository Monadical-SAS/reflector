import argparse
import spacy
from loguru import logger

# Define the paths for agenda and transcription files
def init_argparse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        usage="%(prog)s <AGENDA> <TRANSCRIPTION>",
        description="Compares the transcript of a video or audio file to an agenda using the SpaCy model"
    )
    parser.add_argument("agenda", help="Location of the agenda file")
    parser.add_argument("transcription", help="Location of the transcription file")
    return parser
args = init_argparse().parse_args()
agenda_path = args.agenda
transcription_path = args.transcription

# Load the spaCy model and add the sentencizer
spaCy_model = "en_core_web_md"
nlp = spacy.load(spaCy_model)
nlp.add_pipe('sentencizer')
logger.info("Loaded spaCy model " + spaCy_model )

# Load the agenda
with open(agenda_path, "r") as f:
    agenda = [line.strip() for line in f.readlines() if line.strip()]
logger.info("Loaded agenda items")

# Load the transcription
with open(transcription_path, "r") as f:
    transcription = f.read()
logger.info("Loaded transcription")

# Tokenize the transcription using spaCy
doc_transcription = nlp(transcription)
logger.info("Tokenized transcription")

# Find the items covered in the transcription
covered_items = {}
for item in agenda:
    item_doc = nlp(item)
    for sent in doc_transcription.sents:
        if not sent or not all(token.has_vector for token in sent):
            # Skip an empty span or one without any word vectors
            continue
        similarity = sent.similarity(item_doc)
        similarity_threshold = 0.7
        if similarity > similarity_threshold:  # Set the threshold to determine what is considered a match
            covered_items[item] = True
            break

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
logger.info("Finished comparing agenda to transcription with similarity threshold of " + str(similarity_threshold))
