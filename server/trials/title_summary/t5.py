from transformers import T5ForConditionalGeneration, T5Tokenizer
import torch
# Load the T5 model and tokenizer
model_name = "t5-base"
model = T5ForConditionalGeneration.from_pretrained(model_name)
tokenizer = T5Tokenizer.from_pretrained(model_name)

# Set the device to use
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)

sample_chunks = ["You all just came off of your incredible Google Cloud next conference where you released a wide variety of functionality and features and new products across artisan television and also across the entire sort of cloud ecosystem . You want to just first by walking through , first start by walking through all the innovations that you sort of released and what you 're excited about when you come to Google Cloud ? Now our vision is super simple .  If you look at what smartphones did for a consumer , you know they took a computer and internet browser , a communication device , and a camera , and made it so that it 's in everybody 's pocket , so it really brought computation to every person . We feel that , you know , our , what we 're trying to do is take all the technological innovation that Google 's doing , but make it super simple so that everyone can consume it . And so that includes our global data center footprint , all the new types of hardware and large-scale systems we work on , the software that we 're making available for people to do high-scale computation , tools for data processing , tools for cybersecurity , processing , tools for cyber security , tools for machine learning , but make it so simple that everyone can use it . And every step that we do to simplify things for people , we think adoption can grow . And so that 's a lot of what we 've done these last three , four years , and we made a number of announcements that next in machine learning and AI in particular , you know , we look at our work as four elements , how we take our large-scale compute systems that were building for AI and how we make that available to everybody .  Second , what we 're doing with the software stacks and top of it , things like jacks and other things and how we 're making those available to everybody . Third is advances because different people have different levels of expertise . Some people say I need the hardware to build my own large language model or algorithm . Other people say , look , I really need to use a building block . You guys give me .  So , 30s we 've done a lot with AutoML and we announce new capability for image , video , and translation to make it available to everybody .  And then lastly , we 're also building completely packaged solutions for some areas and we announce some new stuff . ",
                 " We 're joined next by Thomas Curian , CEO of Google Cloud , and Alexander Wang , CEO and founder of Scale AI . Thomas joined Google in November 2018 as the CEO of Google Cloud . Prior to Google , Thomas spent 22 years at Oracle , where most recently he was president of product development . Before that , Thomas worked at McKinsey as a business analyst and engagement manager . His nearly 30 years of experience have given him a deep knowledge of engineering enterprise relationships and leadership of large organizations . Thomas 's degrees include an MBA in administration and management from Stanford University , as an RJ Miller scholar and a BSEE in electrical engineering and computer science from Princeton University , where he graduated suma cum laude .  Thomas serves as a member of the Stanford graduate School of Business Advisory Council and Princeton University School of Engineering Advisory Council . Please welcome to the stage , Thomas Curian and Alexander Wang . This is a super exciting conversation . Thanks for being here , Thomas ."]


# Define the input text for summarization
text = "Summarize the following text in 3 key points. text : " + sample_chunks[1]

# Tokenize the input text
inputs = tokenizer.encode(text, return_tensors="pt").to(device)

# Generate the summary
summary_ids = model.generate(inputs, max_length=1000, num_beams=4, early_stopping=True)

# Decode and print the summary
summary = tokenizer.decode(summary_ids.squeeze(), skip_special_tokens=True)
print("Summary:", summary)
