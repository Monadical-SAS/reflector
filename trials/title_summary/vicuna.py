from gpt4all import GPT4All

model = GPT4All("/Users/gokulmohanarangan/Library/Application Support/nomic.ai/GPT4All/ggml-vicuna-13b-1.1-q4_2.bin")

import spacy


def split_text_file(filename, token_count):
    nlp = spacy.load('en_core_web_md')

    with open(filename, 'r') as file:
        text = file.read()

    doc = nlp(text)
    total_tokens = len(doc)

    parts = []
    start_index = 0

    while start_index < total_tokens:
        end_index = start_index + token_count
        part_tokens = doc[start_index:end_index]
        part = ' '.join(token.text for token in part_tokens)
        parts.append(part)
        start_index = end_index

    return parts

parts = split_text_file("transcript.txt", 1800)
final_summary = []
for part in parts:
       prompt = f"""
              ### Human:
              Summarize the following text without missing any key points and action items.
                     
              {part}
              ### Assistant:
              """
       output = model.generate(prompt)
       final_summary.append(output)


with open("sum.txt", "w") as sum:
       sum.write(" ".join(final_summary))
