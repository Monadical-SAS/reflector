from reflector.processors.base import Processor
from reflector.processors.types import AudioDiarizationInput, TitleSummary, Word


class AudioDiarizationProcessor(Processor):
    INPUT_TYPE = AudioDiarizationInput
    OUTPUT_TYPE = TitleSummary

    async def _push(self, data: AudioDiarizationInput):
        try:
            self.logger.info("Diarization started", audio_file_url=data.audio_url)
            diarization = await self._diarize(data)
            self.logger.info("Diarization finished")
        except Exception:
            self.logger.exception("Diarization failed after retrying")
            raise

        # now reapply speaker to topics (if any)
        # topics is a list[BaseModel] with an attribute words
        # words is a list[BaseModel] with text, start and speaker attribute

        # create a view of words based on topics
        # the current algorithm is using words index, we cannot use a generator
        words = list(self.iter_words_from_topics(data.topics))

        # assign speaker to words (mutate the words list)
        self.assign_speaker(words, diarization)

        # emit them
        for topic in data.topics:
            await self.emit(topic)

    async def _diarize(self, data: AudioDiarizationInput):
        raise NotImplementedError

    def assign_speaker(self, words: list[Word], diarization: list[dict]):
        self._diarization_remove_overlap(diarization)
        self._diarization_remove_segment_without_words(words, diarization)
        self._diarization_merge_same_speaker(words, diarization)
        self._diarization_assign_speaker(words, diarization)

    def iter_words_from_topics(self, topics: TitleSummary):
        for topic in topics:
            for word in topic.transcript.words:
                yield word

    def is_word_continuation(self, word_prev, word):
        """
        Return True if the word is a continuation of the previous word
        by checking if the previous word is ending with a punctuation
        or if the current word is starting with a capital letter
        """
        # is word_prev ending with a punctuation ?
        if word_prev.text and word_prev.text[-1] in ".?!":
            return False
        elif word.text and word.text[0].isupper():
            return False
        return True

    def _diarization_remove_overlap(self, diarization: list[dict]):
        """
        Remove overlap in diarization results

        When using a diarization algorithm, it's possible to have overlapping segments
        This function remove the overlap by keeping the longest segment

        Warning: this function mutate the diarization list
        """
        # remove overlap by keeping the longest segment
        diarization_idx = 0
        while diarization_idx < len(diarization) - 1:
            d = diarization[diarization_idx]
            dnext = diarization[diarization_idx + 1]
            if d["end"] > dnext["start"]:
                # remove the shortest segment
                if d["end"] - d["start"] > dnext["end"] - dnext["start"]:
                    # remove next segment
                    diarization.pop(diarization_idx + 1)
                else:
                    # remove current segment
                    diarization.pop(diarization_idx)
            else:
                diarization_idx += 1

    def _diarization_remove_segment_without_words(
        self, words: list[Word], diarization: list[dict]
    ):
        """
        Remove diarization segments without words

        Warning: this function mutate the diarization list
        """
        # count the number of words for each diarization segment
        diarization_count = []
        for d in diarization:
            start = d["start"]
            end = d["end"]
            count = 0
            for word in words:
                if start <= word.start < end:
                    count += 1
                elif start < word.end <= end:
                    count += 1
            diarization_count.append(count)

        # remove diarization segments with no words
        diarization_idx = 0
        while diarization_idx < len(diarization):
            if diarization_count[diarization_idx] == 0:
                diarization.pop(diarization_idx)
                diarization_count.pop(diarization_idx)
            else:
                diarization_idx += 1

    def _diarization_merge_same_speaker(
        self, words: list[Word], diarization: list[dict]
    ):
        """
        Merge diarization contigous segments with the same speaker

        Warning: this function mutate the diarization list
        """
        # merge segment with same speaker
        diarization_idx = 0
        while diarization_idx < len(diarization) - 1:
            d = diarization[diarization_idx]
            dnext = diarization[diarization_idx + 1]
            if d["speaker"] == dnext["speaker"]:
                diarization[diarization_idx]["end"] = dnext["end"]
                diarization.pop(diarization_idx + 1)
            else:
                diarization_idx += 1

    def _diarization_assign_speaker(self, words: list[Word], diarization: list[dict]):
        """
        Assign speaker to words based on diarization

        Warning: this function mutate the words list
        """

        word_idx = 0
        last_speaker = None
        for d in diarization:
            start = d["start"]
            end = d["end"]
            speaker = d["speaker"]

            # diarization may start after the first set of words
            # in this case, we assign the last speaker
            for word in words[word_idx:]:
                if word.start < start:
                    # speaker change, but what make sense for assigning the word ?
                    # If it's a new sentence, assign with the new speaker
                    # If it's a continuation, assign with the last speaker
                    is_continuation = False
                    if word_idx > 0 and word_idx < len(words) - 1:
                        is_continuation = self.is_word_continuation(
                            *words[word_idx - 1 : word_idx + 1]
                        )
                    if is_continuation:
                        word.speaker = last_speaker
                    else:
                        word.speaker = speaker
                        last_speaker = speaker
                    word_idx += 1
                else:
                    break

            # now continue to assign speaker until the word starts after the end
            for word in words[word_idx:]:
                if start <= word.start < end:
                    last_speaker = speaker
                    word.speaker = speaker
                    word_idx += 1
                elif word.start > end:
                    break

        # no more diarization available,
        # assign last speaker to all words without speaker
        for word in words[word_idx:]:
            word.speaker = last_speaker
