# Approach 1
from transformers import GPTNeoForCausalLM, GPT2Tokenizer

model_name = "EleutherAI/gpt-neo-1.3B"
tokenizer = GPT2Tokenizer.from_pretrained(model_name)
model = GPTNeoForCausalLM.from_pretrained(model_name)

conversation = """
Summarize the following conversation in 3 key sentences:

We 're joined next by Thomas Curian , CEO of Google Cloud , and Alexander Wang , CEO and founder of Scale AI .
Thomas joined Google in November 2018 as the CEO of Google Cloud . Prior to Google , Thomas spent 22 years at Oracle , where most recently he was president of product development .
Before that , Thomas worked at McKinsey as a business analyst and engagement manager . His nearly 30 years of experience have given him a deep knowledge of engineering enterprise relationships and leadership of large organizations .
Thomas 's degrees include an MBA in administration and management from Stanford University , as an RJ Miller scholar and a BSEE in electrical engineering and computer science from Princeton University , where he graduated suma cum laude .
Thomas serves as a member of the Stanford graduate School of Business Advisory Council and Princeton University School of Engineering Advisory Council .
Please welcome to the stage , Thomas Curian and Alexander Wang . This is a super exciting conversation . Thanks for being here , Thomas .
"""

input_ids = tokenizer.encode(conversation, return_tensors="pt")

output = model.generate(input_ids, max_length=30, num_return_sequences=1)

caption = tokenizer.decode(output[0], skip_special_tokens=True)
print("Caption:", caption[len(input_ids) :])


# Approach 2
import torch
from transformers import GPT2LMHeadModel, GPT2Tokenizer

model_name = "gpt2"
tokenizer = GPT2Tokenizer.from_pretrained(model_name)
model = GPT2LMHeadModel.from_pretrained(model_name)

model.eval()

text = """
You all just came off of your incredible Google Cloud next conference where you released a wide variety of functionality and features and new products across artisan television and also across the entire sort of cloud ecosystem . You want to just first by walking through , first start by walking through all the innovations that you sort of released and what you 're excited about when you come to Google Cloud ? Now our vision is super simple .  If you look at what smartphones did for a consumer , you know they took a computer and internet browser , a communication device , and a camera , and made it so that it 's in everybody 's pocket , so it really brought computation to every person . We feel that , you know , our , what we 're trying to do is take all the technological innovation that Google 's doing , but make it super simple so that everyone can consume it . And so that includes our global data center footprint , all the new types of hardware and large-scale systems we work on , the software that we 're making available for people to do high-scale computation , tools for data processing , tools for cybersecurity , processing , tools for cyber security , tools for machine learning , but make it so simple that everyone can use it . And every step that we do to simplify things for people , we think adoption can grow . And so that 's a lot of what we 've done these last three , four years , and we made a number of announcements that next in machine learning and AI in particular , you know , we look at our work as four elements , how we take our large-scale compute systems that were building for AI and how we make that available to everybody .  Second , what we 're doing with the software stacks and top of it , things like jacks and other things and how we 're making those available to everybody . Third is advances because different people have different levels of expertise . Some people say I need the hardware to build my own large language model or algorithm . Other people say , look , I really need to use a building block . You guys give me .  So , 30s we 've done a lot with AutoML and we announce new capability for image , video , and translation to make it available to everybody .  And then lastly , we 're also building completely packaged solutions for some areas and we announce some new stuff . "
"""

tokenizer.pad_token = tokenizer.eos_token
input_ids = tokenizer.encode(text, max_length=100, truncation=True, return_tensors="pt")
attention_mask = torch.ones(input_ids.shape, dtype=torch.long)
output = model.generate(
    input_ids,
    max_new_tokens=20,
    num_return_sequences=1,
    num_beams=2,
    attention_mask=attention_mask,
)

chapter_titles = [
    tokenizer.decode(output[i], skip_special_tokens=True)
    for i in range(output.shape[0])
]
for i, title in enumerate(chapter_titles):
    print("Caption: ", title)

# Approach 3

import torch
from transformers import GPT2LMHeadModel, GPT2Tokenizer


def generate_response(conversation, max_length=100):
    input_text = ""
    for entry in conversation:
        role = entry["role"]
        content = entry["content"]
        input_text += f"{role}: {content}\n"

    # Tokenize the entire conversation
    input_ids = tokenizer.encode(input_text, return_tensors="pt")

    # Generate text based on the entire conversation
    with torch.no_grad():
        output = model.generate(input_ids, pad_token_id=tokenizer.eos_token_id)

    # Decode the generated text and return it
    response = tokenizer.decode(output[0], skip_special_tokens=True)
    return response


if __name__ == "__main__":

    # Call appropriate approach from the main while experimenting
    model_name = "gpt2"
    model = GPT2LMHeadModel.from_pretrained(model_name)
    tokenizer = GPT2Tokenizer.from_pretrained(model_name)

    sample_chunks = [
        "You all just came off of your incredible Google Cloud next conference where you released a wide variety of functionality and features and new products across artisan television and also across the entire sort of cloud ecosystem . You want to just first by walking through , first start by walking through all the innovations that you sort of released and what you 're excited about when you come to Google Cloud ? Now our vision is super simple .  If you look at what smartphones did for a consumer , you know they took a computer and internet browser , a communication device , and a camera , and made it so that it 's in everybody 's pocket , so it really brought computation to every person . We feel that , you know , our , what we 're trying to do is take all the technological innovation that Google 's doing , but make it super simple so that everyone can consume it . And so that includes our global data center footprint , all the new types of hardware and large-scale systems we work on , the software that we 're making available for people to do high-scale computation , tools for data processing , tools for cybersecurity , processing , tools for cyber security , tools for machine learning , but make it so simple that everyone can use it . And every step that we do to simplify things for people , we think adoption can grow . And so that 's a lot of what we 've done these last three , four years , and we made a number of announcements that next in machine learning and AI in particular , you know , we look at our work as four elements , how we take our large-scale compute systems that were building for AI and how we make that available to everybody .  Second , what we 're doing with the software stacks and top of it , things like jacks and other things and how we 're making those available to everybody . Third is advances because different people have different levels of expertise . Some people say I need the hardware to build my own large language model or algorithm . Other people say , look , I really need to use a building block . You guys give me .  So , 30s we 've done a lot with AutoML and we announce new capability for image , video , and translation to make it available to everybody .  And then lastly , we 're also building completely packaged solutions for some areas and we announce some new stuff . "
    ]

    conversation = [
        {"role": "system", "content": "Summarize this text"},
        {"role": "user", "content": " text : " + sample_chunks[0]},
    ]

    response = generate_response(conversation)
    print("Response:", response)
