import torch
from transformers import BertTokenizer, BertModel
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# Load the pre-trained BERT model and tokenizer
model_name = "bert-base-uncased"
model = BertModel.from_pretrained(model_name)
tokenizer = BertTokenizer.from_pretrained(model_name)

# Set the device to use
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)

# Load the SentenceTransformer model
sentence_transformer_model = SentenceTransformer(
    "average_word_embeddings_glove.6B.300d"
)

# Define the input text
text = "Your input text to be summarized goes here."

# Tokenize the text
tokens = tokenizer.tokenize(text)
input_ids = tokenizer.convert_tokens_to_ids(tokens)
input_ids = torch.tensor([input_ids]).to(device)

# Get the BERT model output
with torch.no_grad():
    outputs = model(input_ids)[0]  # Extract the last hidden states

# Calculate sentence embeddings
sentence_embeddings = outputs.mean(dim=1).squeeze().cpu().numpy()
input_text_embedding = sentence_transformer_model.encode([text])[0]

# Calculate cosine similarity between sentences and input text
similarity_scores = cosine_similarity([input_text_embedding], sentence_embeddings)

# Sort the sentences by similarity scores in descending order
sorted_sentences = [
    sent for _, sent in sorted(zip(similarity_scores[0], sentences), reverse=True)
]

# Choose the top sentences as the summary
num_summary_sentences = 2  # Adjust as needed
summary = ". ".join(sorted_sentences[:num_summary_sentences])
print("Summary:", summary)
