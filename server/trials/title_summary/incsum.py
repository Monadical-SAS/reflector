import spacy
import sys


# Observe the incremental summaries by performing summaries in chunks
with open("transcript.txt", "r", encoding="utf-8") as file:
    transcription = file.read()


def split_text_file(filename, token_count):
    nlp = spacy.load("en_core_web_md")

    with open(filename, "r", encoding="utf-8") as file:
        text = file.read()

    doc = nlp(text)
    total_tokens = len(doc)

    parts = []
    start_index = 0

    while start_index < total_tokens:
        end_index = start_index + token_count
        part_tokens = doc[start_index:end_index]
        part = " ".join(token.text for token in part_tokens)
        parts.append(part)
        start_index = end_index

    return parts


# Set the chunk length here to split the transcript and test
MAX_CHUNK_LENGTH = 1000

chunks = split_text_file("transcript.txt", MAX_CHUNK_LENGTH)
print("Number of chunks", len(chunks))

# Write chunks to file to refer to input vs output, separated by blank lines
with open("chunks" + str(MAX_CHUNK_LENGTH) + ".txt", "a", encoding="utf-8") as file:
    for c in chunks:
        file.write(c + "\n\n")

# If we want to run only a certain model, type the option while running
# ex. python incsum.py 1 => will run approach 1
# If no input, will run all approaches

try:
    index = sys.argv[1]
except:
    index = None

# Approach 1 : facebook/bart-large-cnn
if index == "1" or index is None:
    SUMMARY_MODEL = "facebook/bart-large-cnn"
    MIN_LENGTH = 5
    MAX_LENGTH = 10
    BEAM_SIZE = 2

    print("Performing chunk summary : " + SUMMARY_MODEL)

    from transformers import BartTokenizer, BartForConditionalGeneration

    tokenizer = BartTokenizer.from_pretrained(SUMMARY_MODEL)
    model = BartForConditionalGeneration.from_pretrained(SUMMARY_MODEL)
    summaries = []
    for c in chunks:
        input_ids = tokenizer.encode(
            c,
            truncation=True,
            max_length=MAX_CHUNK_LENGTH,
            padding="max_length",
            return_tensors="pt",
        )
        summary_ids = model.generate(
            input_ids,
            num_beams=BEAM_SIZE,
            max_length=56,
            early_stopping=True,
            length_penalty=1.0,
        )
        summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
        summaries.append(summary)

    with open("bart-summaries.txt", "a", encoding="utf-8") as file:
        for summary in summaries:
            file.write(summary + "\n\n")

# Approach 2
if index == "2" or index is None:
    print("Performing chunk summary : " + "gpt-neo-1.3B")

    import torch
    from transformers import GPTNeoForCausalLM, GPT2Tokenizer

    model = GPTNeoForCausalLM.from_pretrained("EleutherAI/gpt-neo-1.3B")
    tokenizer = GPT2Tokenizer.from_pretrained("EleutherAI/gpt-neo-1.3B")
    tokenizer.add_special_tokens({"pad_token": "[PAD]"})
    summaries = []

    for c in chunks:
        input_ids = tokenizer.encode(c, truncation=True, return_tensors="pt")
        input_length = input_ids.shape[1]
        attention_mask = torch.ones(input_ids.shape, dtype=torch.long)

        max_summary_length = 100
        max_length = input_length + max_summary_length

        output = model.generate(
            input_ids,
            max_length=max_length,
            attention_mask=attention_mask,
            pad_token_id=model.config.eos_token_id,
            num_beams=4,
            length_penalty=2.0,
            early_stopping=True,
        )
        summary_ids = output[0, input_length:]
        summary = tokenizer.decode(summary_ids, skip_special_tokens=True)
        summaries.append(summary)
        with open("gptneo1.3B-summaries.txt", "a", encoding="utf-8") as file:
            file.write(summary + "\n\n")

# Approach 3
if index == "3" or index is None:
    print("Performing chunk summary : " + "mpt-7B")

    import torch
    import transformers
    from transformers import AutoTokenizer

    config = transformers.AutoConfig.from_pretrained(
        "mosaicml/mpt-7b", trust_remote_code=True
    )
    config.attn_config["attn_impl"] = "triton"
    config.max_seq_len = 1024
    config.init_device = "meta"

    model = transformers.AutoModelForCausalLM.from_pretrained(
        "mosaicml/mpt-7b", trust_remote_code=True, torch_dtype=torch.bfloat16
    )

    tokenizer = AutoTokenizer.from_pretrained("EleutherAI/gpt-neox-20b")

    summaries = []
    for c in chunks:
        input_ids = tokenizer.encode(c, return_tensors="pt")
        attention_mask = torch.ones(input_ids.shape, dtype=torch.long)
        output = model.generate(
            input_ids,
            max_new_tokens=25,
            attention_mask=attention_mask,
            pad_token_id=model.config.eos_token_id,
            num_return_sequences=1,
        )
        summary = tokenizer.decode(output[0], skip_special_tokens=True)
        summaries.append(summary)

    with open("mpt-7b-summaries.txt", "a", encoding="utf-8") as file:
        for summary in summaries:
            file.write(summary + "\n\n")
