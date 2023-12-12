import { faArrowTurnDown, faSpinner } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { ChangeEvent, useEffect, useRef, useState } from "react";
import { Participant } from "../../../../api";
import getApi from "../../../../lib/getApi";
import { UseParticipants } from "../../useParticipants";
import { selectedTextIsSpeaker, selectedTextIsTimeSlice } from "./page";

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
          setSelectedParticipant(participant);
          inputRef.current?.focus();
          setAction("Rename");
        } else if (!selectedParticipant) {
          setSelectedParticipant(undefined);
          setParticipantInput("");
          inputRef.current?.focus();
          setAction("Create to rename");
        }
      }
      if (selectedTextIsTimeSlice(selectedText)) {
        setParticipantInput("");
        inputRef.current?.focus();
        setAction("Create and assign");
        setSelectedParticipant(undefined);
      }
      if (typeof selectedText == undefined) {
        setAction(null);
      }
    }
  }, [selectedText, participants]);

  useEffect(() => {
    document.onkeyup = (e) => {
      if (loading || participants.loading || topicWithWords.loading) return;
      if (e.key === "Enter" && e.ctrlKey) {
        if (oneMatch) {
          if (action == "Create and assign") {
            assignTo(oneMatch)();
            setOneMatch(undefined);
            setParticipantInput("");
          } else if (
            action == "Create to rename" &&
            oneMatch &&
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

  const mergeSpeaker =
    (speakerFrom, participantTo: Participant) => async () => {
      if (loading || participants.loading || topicWithWords.loading) return;
      if (participantTo.speaker) {
        setLoading(true);
        await api?.v1TranscriptMergeSpeaker({
          transcriptId,
          speakerMerge: {
            speakerFrom: speakerFrom,
            speakerTo: participantTo.speaker,
          },
        });
      } else {
        await api?.v1TranscriptUpdateParticipant({
          transcriptId,
          participantId: participantTo.id,
          updateParticipant: { speaker: speakerFrom },
        });
      }
      participants.refetch();
      topicWithWords.refetch();
      setAction(null);
      setParticipantInput("");
      setLoading(false);
    };

  const doAction = (e?) => {
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
          setLoading(false);
        });
    } else if (
      action == "Create and assign" &&
      selectedTextIsTimeSlice(selectedText)
    ) {
      setLoading(true);
      api
        ?.v1TranscriptAddParticipant({
          createParticipant: {
            name: participantInput,
          },
          transcriptId,
        })
        .then((participant) => {
          setLoading(false);
          assignTo(participant)();
          setParticipantInput("");
        });
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
      });
  };

  const assignTo =
    (participant) => (e?: React.MouseEvent<HTMLButtonElement>) => {
      e?.preventDefault();
      e?.stopPropagation();
      if (loading || participants.loading || topicWithWords.loading) return;
      if (!selectedTextIsTimeSlice(selectedText)) return;

      setLoading(true);
      api
        ?.v1TranscriptAssignSpeaker({
          speakerAssignment: {
            participant: participant.id,
            timestampFrom: selectedText.start,
            timestampTo: selectedText.end,
          },
          transcriptId,
        })
        .then(() => {
          topicWithWords.refetch();
          participants.refetch();
          setLoading(false);
          setAction(null);
          setSelectedText(undefined);
          setSelectedParticipant(undefined);
        });
    };

  const selectParticipant = (participant) => (e) => {
    setSelectedParticipant(participant);
    setSelectedText(participant.speaker);
    setAction("Rename");
    setParticipantInput(participant.name);
  };

  const clearSelection = () => {
    setSelectedParticipant(undefined);
    setSelectedText(undefined);
    setAction(null);
    setParticipantInput("");
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
        <div className="grid grid-cols-2 gap-2 mb-2">
          <input
            ref={inputRef}
            onChange={changeParticipantInput}
            value={participantInput}
            className="border border-blue-400 p-1"
          />
          {action && (
            <button onClick={doAction} className="p-2 bg-blue-200 w-full">
              [
              <FontAwesomeIcon
                icon={faArrowTurnDown}
                className="rotate-90 h-2"
              />
              ]{" " + action}
            </button>
          )}
        </div>

        {loading ||
          participants.loading ||
          (topicWithWords.loading && (
            <FontAwesomeIcon
              icon={faSpinner}
              className="animate-spin-slow text-gray-300 h-8"
            />
          ))}
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
