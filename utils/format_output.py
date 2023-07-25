import json

with open("../artefacts/meeting_titles_and_summaries.txt", "r") as f:
    outputs = f.read()

outputs = json.loads(outputs)

transcript_file = open("../artefacts/meeting_transcript.txt", "a")
title_desc_file = open("../artefacts/meeting_title_description.txt", "a")
summary_file = open("../artefacts/meeting_summary.txt", "a")

for item in outputs["topics"]:
    transcript_file.write(item["transcript"])
    summary_file.write(item["description"])

    title_desc_file.write("TITLE: \n")
    title_desc_file.write(item["title"])
    title_desc_file.write("\n")

    title_desc_file.write("DESCRIPTION: \n")
    title_desc_file.write(item["description"])
    title_desc_file.write("\n")

    title_desc_file.write("TRANSCRIPT: \n")
    title_desc_file.write(item["transcript"])
    title_desc_file.write("\n")

    title_desc_file.write("---------------------------------------- \n\n")

transcript_file.close()
title_desc_file.close()
summary_file.close()
