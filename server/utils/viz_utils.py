"""
Utility file for all visualization related functions
"""

import ast
import collections
import os
import pickle

import matplotlib.pyplot as plt
import pandas as pd
import scattertext as st
import spacy
from nltk.corpus import stopwords
from wordcloud import STOPWORDS, WordCloud

en = spacy.load('en_core_web_md')
spacy_stopwords = en.Defaults.stop_words

STOPWORDS = set(STOPWORDS).union(set(stopwords.words("english"))). \
    union(set(spacy_stopwords))


def create_wordcloud(timestamp, real_time=False):
    """
    Create a basic word cloud visualization of transcribed text
    :return: None. The wordcloud image is saved locally
    """
    filename = "transcript"
    if real_time:
        filename = "real_time_" + filename + "_" + \
                   timestamp.strftime("%m-%d-%Y_%H:%M:%S") + ".txt"
    else:
        filename += "_" + timestamp.strftime("%m-%d-%Y_%H:%M:%S") + ".txt"

    with open("./artefacts/" + filename, "r") as f:
        transcription_text = f.read()

    # python_mask = np.array(PIL.Image.open("download1.png"))

    wordcloud = WordCloud(height=800, width=800,
                          background_color='white',
                          stopwords=STOPWORDS,
                          min_font_size=8).generate(transcription_text)

    # Plot wordcloud and save image
    plt.figure(facecolor=None)
    plt.imshow(wordcloud, interpolation="bilinear")
    plt.axis("off")
    plt.tight_layout(pad=0)

    wordcloud = "wordcloud"
    if real_time:
        wordcloud = "real_time_" + wordcloud + "_" + \
                         timestamp.strftime("%m-%d-%Y_%H:%M:%S") + ".png"
    else:
        wordcloud += "_" + timestamp.strftime("%m-%d-%Y_%H:%M:%S") + ".png"

    plt.savefig("./artefacts/" + wordcloud)


def create_talk_diff_scatter_viz(timestamp, real_time=False):
    """
    Perform agenda vs transcription diff to see covered topics.
    Create a scatter plot of words in topics.
    :return: None. Saved locally.
    """
    spacy_model = "en_core_web_md"
    nlp = spacy.load(spacy_model)
    nlp.add_pipe('sentencizer')

    agenda_topics = []
    agenda = []
    # Load the agenda
    with open(os.path.join(os.getcwd(), "agenda-headers.txt"), "r") as f:
        for line in f.readlines():
            if line.strip():
                agenda.append(line.strip())
                agenda_topics.append(line.split(":")[0])

    # Load the transcription with timestamp
    if real_time:
        filename = "./artefacts/real_time_transcript_with_timestamp_" + \
                   timestamp.strftime("%m-%d-%Y_%H:%M:%S") + ".txt"
    else:
        filename = "./artefacts/transcript_with_timestamp_" + \
                   timestamp.strftime("%m-%d-%Y_%H:%M:%S") + ".txt"
    with open(filename) as file:
        transcription_timestamp_text = file.read()

    res = ast.literal_eval(transcription_timestamp_text)
    chunks = res["chunks"]

    # create df for processing
    df = pd.DataFrame.from_dict(res["chunks"])

    covered_items = {}
    # ts: timestamp
    # Map each timestamped chunk with top1 and top2 matched agenda
    ts_to_topic_mapping_top_1 = {}
    ts_to_topic_mapping_top_2 = {}

    # Also create a mapping of the different timestamps
    # in which each topic was covered
    topic_to_ts_mapping_top_1 = collections.defaultdict(list)
    topic_to_ts_mapping_top_2 = collections.defaultdict(list)

    similarity_threshold = 0.7

    for c in chunks:
        doc_transcription = nlp(c["text"])
        topic_similarities = []
        for item in range(len(agenda)):
            item_doc = nlp(agenda[item])
            # if not doc_transcription or not all
            # (token.has_vector for token in doc_transcription):
            if not doc_transcription:
                continue
            similarity = doc_transcription.similarity(item_doc)
            topic_similarities.append((item, similarity))
        topic_similarities.sort(key=lambda x: x[1], reverse=True)
        for i in range(2):
            if topic_similarities[i][1] >= similarity_threshold:
                covered_items[agenda[topic_similarities[i][0]]] = True
            # top1 match
            if i == 0:
                ts_to_topic_mapping_top_1[c["timestamp"]] = agenda_topics[topic_similarities[i][0]]
                topic_to_ts_mapping_top_1[agenda_topics[topic_similarities[i][0]]].append(c["timestamp"])
            # top2 match
            else:
                ts_to_topic_mapping_top_2[c["timestamp"]] = agenda_topics[topic_similarities[i][0]]
                topic_to_ts_mapping_top_2[agenda_topics[topic_similarities[i][0]]].append(c["timestamp"])

    def create_new_columns(record):
        """
        Accumulate the mapping information into the df
        :param record:
        :return:
        """
        record["ts_to_topic_mapping_top_1"] = \
            ts_to_topic_mapping_top_1[record["timestamp"]]
        record["ts_to_topic_mapping_top_2"] = \
            ts_to_topic_mapping_top_2[record["timestamp"]]
        return record

    df = df.apply(create_new_columns, axis=1)

    # Count the number of items covered and calculate the percentage
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

    # Save df, mappings for further experimentation
    df_name = "df"
    if real_time:
        df_name = "real_time_" + df_name + "_" + \
                  timestamp.strftime("%m-%d-%Y_%H:%M:%S") + ".pkl"
    else:
        df_name += "_" + timestamp.strftime("%m-%d-%Y_%H:%M:%S") + ".pkl"
    df.to_pickle("./artefacts/" + df_name)

    my_mappings = [ts_to_topic_mapping_top_1, ts_to_topic_mapping_top_2,
                   topic_to_ts_mapping_top_1, topic_to_ts_mapping_top_2]

    mappings_name = "mappings"
    if real_time:
        mappings_name = "real_time_" + mappings_name + "_" + \
                        timestamp.strftime("%m-%d-%Y_%H:%M:%S") + ".pkl"
    else:
        mappings_name += "_" + timestamp.strftime("%m-%d-%Y_%H:%M:%S") + ".pkl"
    pickle.dump(my_mappings, open("./artefacts/" + mappings_name, "wb"))

    # to load,  my_mappings = pickle.load( open ("mappings.pkl", "rb") )

    # pick the 2 most matched topic to be used for plotting
    topic_times = collections.defaultdict(int)
    for key in ts_to_topic_mapping_top_1.keys():
        if key[0] is None or key[1] is None:
            continue
        duration = key[1] - key[0]
        topic_times[ts_to_topic_mapping_top_1[key]] += duration

    topic_times = sorted(topic_times.items(), key=lambda x: x[1], reverse=True)

    if len(topic_times) > 1:
        cat_1 = topic_times[0][0]
        cat_1_name = topic_times[0][0]
        cat_2_name = topic_times[1][0]

        # Scatter plot of topics
        df = df.assign(parse=lambda df: df.text.apply(st.whitespace_nlp_with_sentences))
        corpus = st.CorpusFromParsedDocuments(
                df, category_col='ts_to_topic_mapping_top_1', parsed_col='parse'
        ).build().get_unigram_corpus().compact(st.AssociationCompactor(2000))
        html = st.produce_scattertext_explorer(
                corpus,
                category=cat_1,
                category_name=cat_1_name,
                not_category_name=cat_2_name,
                minimum_term_frequency=0, pmi_threshold_coefficient=0,
                width_in_pixels=1000,
                transform=st.Scalers.dense_rank
        )
        if real_time:
            open('./artefacts/real_time_scatter_' +
                 timestamp.strftime("%m-%d-%Y_%H:%M:%S") + '.html', 'w').write(html)
        else:
            open('./artefacts/scatter_' +
                 timestamp.strftime("%m-%d-%Y_%H:%M:%S") + '.html', 'w').write(html)
