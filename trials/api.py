import requests
import spacy

# This is the URL of text-generation-webui
URL = "http://216.153.52.83:5000/api/v1/generate"

headers = {
    "Content-Type": "application/json"
}


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
        part_tokens = doc[start_index:end_index-5]
        part = ' '.join(token.text for token in part_tokens)
        parts.append(part)
        start_index = end_index

    return parts


final_summary = ""
parts = split_text_file("transcript.txt", 1600)
previous_summary = ""

for part in parts:
    prompt = f"""
              ### Human:
             Given the following text, distill the most important information 
             into a short summary:  {part}

              ### Assistant:
              """
    data = {
            "prompt": prompt
    }
    try:
        response = requests.post(URL, headers=headers, json=data)
        print(response.json())
    except Exception as e:
        print(str(e))

with open("sum.txt", "w") as sum:
    sum.write(" ".join(final_summary))