from transformers import AutoTokenizer, AutoModelForCausalLM

# tokenizer = AutoTokenizer.from_pretrained("CarperAI/stable-vicuna-13b-delta")
# model = AutoModelForCausalLM.from_pretrained("CarperAI/stable-vicuna-13b-delta")

tokenizer = AutoTokenizer.from_pretrained("lmsys/vicuna-13b-v1.3")
model = AutoModelForCausalLM.from_pretrained("lmsys/vicuna-13b-v1.3")
# model.half().cuda()

prompt = """\
Summarize the text in a subject line. text = "You all just came off of your incredible Google Cloud next conference where you released a wide variety of functionality and features and new products across artisan television and also across the entire sort of cloud ecosystem . You want to just first by walking through , first start by walking through all the innovations that you sort of released and what you 're excited about when you come to Google Cloud ? Now our vision is super simple .  If you look at what smartphones did for a consumer , you know they took a computer and internet browser , a communication device , and a camera , and made it so that it 's in everybody 's pocket , so it really brought computation to every person . We feel that , you know , our , what we 're trying to do is take all the technological innovation that Google 's doing , but make it super simple so that everyone can consume it . And so that includes our global data center footprint , all the new types of hardware and large-scale systems we work on , the software that we 're making available for people to do high-scale computation , tools for data processing , tools for cybersecurity , processing , tools for cyber security , tools for machine learning , but make it so simple that everyone can use it . And every step that we do to simplify things for people , we think adoption can grow . And so that 's a lot of what we 've done these last three , four years , and we made a number of announcements that next in machine learning and AI in particular , you know , we look at our work as four elements , how we take our large-scale compute systems that were building for AI and how we make that available to everybody .  Second , what we 're doing with the software stacks and top of it , things like jacks and other things and how we 're making those available to everybody . Third is advances because different people have different levels of expertise . Some people say I need the hardware to build my own large language model or algorithm . Other people say , look , I really need to use a building block . You guys give me .  So , 30s we 've done a lot with AutoML and we announce new capability for image , video , and translation to make it available to everybody .  And then lastly , we 're also building completely packaged solutions for some areas and we announce some new stuff . "
"""

inputs = tokenizer(prompt, return_tensors='pt')
tokens = model.generate(
 inputs,
 max_new_tokens=256
)
print(tokenizer.decode(tokens[0], skip_special_tokens=True))
