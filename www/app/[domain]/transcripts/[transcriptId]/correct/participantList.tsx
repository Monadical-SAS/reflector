import { faArrowTurnDown, faSpinner } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { ChangeEvent, useEffect, useRef, useState } from "react";
import { Participant } from "../../../../api";
import getApi from "../../../../lib/getApi";
import { UseParticipants } from "../../useParticipants";
import { selectedTextIsSpeaker, selectedTextIsTimeSlice } from "./types";
import { useError } from "../../../../(errors)/errorContext";

type ParticipantList = {
  participants: UseParticipants;
  transcriptId: string;
  topicWithWords: any;
  stateSelectedText: any;
};
// NTH re-order list when searching
const ParticipantList = ({
  transcriptId,
  participants,
  topicWithWords,
  stateSelectedText,
}: ParticipantList) => {
  const api = getApi();
  const { setError } = useError();
  const [loading, setLoading] = useState(false);
  const [participantInput, setParticipantInput] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const [selectedText, setSelectedText] = stateSelectedText;
  const [selectedParticipant, setSelectedParticipant] = useState<Participant>();
  const [action, setAction] = useState<
    "Create" | "Create to rename" | "Create and assign" | "Rename" | null
  >(null);
  const [oneMatch, setOneMatch] = useState<Participant>();

  useEffect(() => {
    if (participants.response) {
      if (selectedTextIsSpeaker(selectedText)) {
        inputRef.current?.focus();
        const participant = participants.response.find(
          (p) => p.speaker == selectedText,
        );
        if (participant) {
          setParticipantInput(participant.name);
          setOneMatch(undefined);
          setSelectedParticipant(participant);
          setAction("Rename");
        } else {
          setSelectedParticipant(participant);
          setParticipantInput("");
          setOneMatch(undefined);
          setAction("Create to rename");
        }
      }
      if (selectedTextIsTimeSlice(selectedText)) {
        inputRef.current?.focus();
        setParticipantInput("");
        setOneMatch(undefined);
        setAction("Create and assign");
        setSelectedParticipant(undefined);
      }
      if (typeof selectedText == undefined) {
        inputRef.current?.blur();
        setAction(null);
      }
    }
  }, [selectedText, participants.response]);

  useEffect(() => {
    document.onkeyup = (e) => {
      if (loading || participants.loading || topicWithWords.loading) return;
      if (e.key === "Enter" && e.ctrlKey) {
        if (oneMatch) {
          if (
            action == "Create and assign" &&
            selectedTextIsTimeSlice(selectedText)
          ) {
            assignTo(oneMatch)().catch(() => {});
          } else if (
            action == "Create to rename" &&
            selectedTextIsSpeaker(selectedText)
          ) {
            mergeSpeaker(selectedText, oneMatch)();
          }
        }
      } else if (e.key === "Enter") {
        doAction();
      }
    };
  });

  const onSuccess = () => {
    topicWithWords.refetch();
    participants.refetch();
    setLoading(false);
    setAction(null);
    setSelectedText(undefined);
    setSelectedParticipant(undefined);
    setParticipantInput("");
    setOneMatch(undefined);
    inputRef?.current?.blur();
  };

  const assignTo =
    (participant) => async (e?: React.MouseEvent<HTMLButtonElement>) => {
      e?.preventDefault();
      e?.stopPropagation();

      if (loading || participants.loading || topicWithWords.loading) return;
      if (!selectedTextIsTimeSlice(selectedText)) return;

      setLoading(true);
      try {
        await api?.v1TranscriptAssignSpeaker({
          speakerAssignment: {
            participant: participant.id,
            timestampFrom: selectedText.start,
            timestampTo: selectedText.end,
          },
          transcriptId,
        });
        onSuccess();
      } catch (error) {
        setError(error, "There was an error assigning");
        setLoading(false);
        throw error;
      }
    };

  const mergeSpeaker =
    (speakerFrom, participantTo: Participant) => async () => {
      if (loading || participants.loading || topicWithWords.loading) return;
      setLoading(true);
      if (participantTo.speaker) {
        try {
          await api?.v1TranscriptMergeSpeaker({
            transcriptId,
            speakerMerge: {
              speakerFrom: speakerFrom,
              speakerTo: participantTo.speaker,
            },
          });
          onSuccess();
        } catch (error) {
          setError(error, "There was an error merging");
          setLoading(false);
        }
      } else {
        try {
          await api?.v1TranscriptUpdateParticipant({
            transcriptId,
            participantId: participantTo.id,
            updateParticipant: { speaker: speakerFrom },
          });
          onSuccess();
        } catch (error) {
          setError(error, "There was an error merging (update)");
          setLoading(false);
        }
      }
    };

  const doAction = async (e?) => {
    e?.preventDefault();
    e?.stopPropagation();
    if (
      loading ||
      participants.loading ||
      topicWithWords.loading ||
      !participants.response
    )
      return;
    if (action == "Rename" && selectedTextIsSpeaker(selectedText)) {
      const participant = participants.response.find(
        (p) => p.speaker == selectedText,
      );
      if (participant && participant.name !== participantInput) {
        setLoading(true);
        api
          ?.v1TranscriptUpdateParticipant({
            participantId: participant.id,
            transcriptId,
            updateParticipant: {
              name: participantInput,
            },
          })
          .then(() => {
            participants.refetch();
            setLoading(false);
            setAction(null);
          })
          .catch((e) => {
            setError(e, "There was an error renaming");
            setLoading(false);
          });
      }
    } else if (
      action == "Create to rename" &&
      selectedTextIsSpeaker(selectedText)
    ) {
      setLoading(true);
      api
        ?.v1TranscriptAddParticipant({
          createParticipant: {
            name: participantInput,
            speaker: selectedText,
          },
          transcriptId,
        })
        .then(() => {
          participants.refetch();
          setParticipantInput("");
          setOneMatch(undefined);
          setLoading(false);
        })
        .catch((e) => {
          setError(e, "There was an error creating");
          setLoading(false);
        });
    } else if (
      action == "Create and assign" &&
      selectedTextIsTimeSlice(selectedText)
    ) {
      setLoading(true);
      try {
        const participant = await api?.v1TranscriptAddParticipant({
          createParticipant: {
            name: participantInput,
          },
          transcriptId,
        });
        setLoading(false);
        assignTo(participant)().catch(() => {
          // error and loading are handled by assignTo catch
          participants.refetch();
        });
      } catch (error) {
        setError(e, "There was an error creating");
        setLoading(false);
      }
    } else if (action == "Create") {
      setLoading(true);
      api
        ?.v1TranscriptAddParticipant({
          createParticipant: {
            name: participantInput,
          },
          transcriptId,
        })
        .then(() => {
          participants.refetch();
          setParticipantInput("");
          setLoading(false);
        })
        .catch((e) => {
          setError(e, "There was an error creating");
          setLoading(false);
        });
    }
  };

  const deleteParticipant = (participantId) => (e) => {
    e.stopPropagation();
    if (loading || participants.loading || topicWithWords.loading) return;
    setLoading(true);
    api
      ?.v1TranscriptDeleteParticipant({
        transcriptId,
        participantId,
      })
      .then(() => {
        participants.refetch();
        setLoading(false);
      })
      .catch((e) => {
        setError(e, "There was an error deleting");
        setLoading(false);
      });
  };

  const selectParticipant = (participant) => (e) => {
    setSelectedParticipant(participant);
    setSelectedText(participant.speaker);
    setAction("Rename");
    setParticipantInput(participant.name);
    oneMatch && setOneMatch(undefined);
  };

  const clearSelection = () => {
    setSelectedParticipant(undefined);
    setSelectedText(undefined);
    setAction(null);
    setParticipantInput("");
    oneMatch && setOneMatch(undefined);
  };
  const preventClick = (e) => {
    e?.stopPropagation();
    e?.preventDefault();
  };
  const changeParticipantInput = (e: ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value.replaceAll(/,|\.| /g, "");
    setParticipantInput(value);
    if (
      value.length > 0 &&
      participants.response &&
      (action == "Create and assign" || action == "Create to rename")
    ) {
      if (
        participants.response.filter((p) => p.name.startsWith(value)).length ==
        1
      ) {
        setOneMatch(
          participants.response.find((p) => p.name.startsWith(value)),
        );
      } else {
        setOneMatch(undefined);
      }
    }
    if (value.length > 0 && !action) {
      setAction("Create");
    }
  };

  return (
    <div className="h-full" onClick={clearSelection}>
      <div onClick={preventClick}>
        <div className="grid grid-cols-7 gap-2 mb-2">
          <input
            ref={inputRef}
            onChange={changeParticipantInput}
            value={participantInput}
            className="border col-span-3 border-blue-400 p-1"
          />
          {action ? (
            <button
              onClick={doAction}
              className="p-2 bg-blue-200 w-full col-span-3"
            >
              [
              <FontAwesomeIcon
                icon={faArrowTurnDown}
                className="rotate-90 h-2"
              />
              ]{" " + action}
            </button>
          ) : (
            <div className="col-span-3" />
          )}
          {loading ||
            participants.loading ||
            (topicWithWords.loading && (
              <FontAwesomeIcon
                icon={faSpinner}
                className="animate-spin-slow text-gray-300 h-8"
              />
            ))}
        </div>

        {participants.response && (
          <ul>
            {participants.response.map((participant: Participant) => (
              <li
                onClick={selectParticipant(participant)}
                className={
                  "flex flex-row justify-between border-b last:border-b-0 py-2 " +
                  (participantInput.length > 0 &&
                  selectedText &&
                  participant.name.startsWith(participantInput)
                    ? "bg-blue-100 "
                    : "") +
                  (participant.id == selectedParticipant?.id
                    ? "bg-blue-200 border"
                    : "")
                }
                key={participant.id}
              >
                <span>{participant.name}</span>

                <div>
                  {selectedTextIsSpeaker(selectedText) &&
                    !selectedParticipant &&
                    !loading && (
                      <button
                        onClick={mergeSpeaker(selectedText, participant)}
                        className="bg-blue-400 px-2 ml-2"
                      >
                        {oneMatch?.id == participant.id &&
                          action == "Create to rename" && (
                            <>
                              <span className="text-xs">
                                [CTRL +{" "}
                                <FontAwesomeIcon
                                  icon={faArrowTurnDown}
                                  className="rotate-90 mr-2 h-2"
                                />
                                ]
                              </span>
                            </>
                          )}{" "}
                        Merge
                      </button>
                    )}
                  {selectedTextIsTimeSlice(selectedText) && !loading && (
                    <button
                      onClick={assignTo(participant)}
                      className="bg-blue-400 px-2 ml-2"
                    >
                      {oneMatch?.id == participant.id &&
                        action == "Create and assign" && (
                          <>
                            <span className="text-xs">
                              [CTRL +{" "}
                              <FontAwesomeIcon
                                icon={faArrowTurnDown}
                                className="rotate-90 mr-2 h-2"
                              />
                              ]
                            </span>
                          </>
                        )}{" "}
                      Assign
                    </button>
                  )}

                  <button
                    onClick={deleteParticipant(participant.id)}
                    className="bg-blue-400 px-2 ml-2"
                  >
                    Delete
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
};

export default ParticipantList;
