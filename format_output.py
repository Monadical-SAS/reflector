import json

with open("meeting_titles_and_summaries.txt", "r") as f:
    outputs = f.read()

outputs = json.loads(outputs)

transcript_file = open("meeting_transcript.txt", "a")
title_description_file = open("meeting_title_description.txt", "a")

for item in outputs["topics"]:
    transcript_file.write(item["transcript"])

    title_description_file.write("TITLE: \n")
    title_description_file.write(item["title"])
    title_description_file.write("\n")

    title_description_file.write("DESCRIPTION: \n")
    title_description_file.write(item["description"])
    title_description_file.write("\n")

    title_description_file.write("TRANSCRIPT: \n")
    title_description_file.write(item["transcript"])
    title_description_file.write("\n")

    title_description_file.write("---------------------------------------- \n\n")




