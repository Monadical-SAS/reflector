import { faArrowTurnDown, faSpinner } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { useEffect, useRef, useState } from "react";
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
    if (loading) {
      setLoading(false);
    }
  }, [participants.loading]);

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
  }, [selectedText]);

  useEffect(() => {
    if (
      participants.response &&
      (action == "Create and assign" || action == "Create to rename")
    ) {
      if (
        participants.response.filter((p) => p.name.startsWith(participantInput))
          .length == 1
      ) {
        setOneMatch(
          participants.response.find((p) =>
            p.name.startsWith(participantInput),
          ),
        );
      } else {
        setOneMatch(undefined);
      }
    }
    if (participantInput && !action) {
      setAction("Create");
    }
  }, [participantInput]);

  useEffect(() => {
    document.onkeyup = (e) => {
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
      if (participantTo.speaker) {
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
    };

  const doAction = (e?) => {
    e?.preventDefault();
    e?.stopPropagation();
    if (!participants.response) return;
    if (action == "Rename" && selectedTextIsSpeaker(selectedText)) {
      const participant = participants.response.find(
        (p) => p.speaker == selectedText,
      );
      if (participant && participant.name !== participantInput) {
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
          assignTo(participant)();
          participants.refetch();
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
        });
    }
  };

  const deleteParticipant = (participantId) => () => {
    if (!loading) {
      api
        ?.v1TranscriptDeleteParticipant({
          transcriptId,
          participantId,
        })
        .then(() => {
          participants.refetch();
        });
    }
  };

  const assignTo =
    (participant) => (e?: React.MouseEvent<HTMLButtonElement>) => {
      e?.preventDefault();
      e?.stopPropagation();
      // fix participant that doesnt have a speaker (wait API)
      if (!selectedTextIsTimeSlice(selectedText)) return;

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
  };
  const preventClick = (e) => {
    e?.stopPropagation();
    e?.preventDefault();
  };

  return (
    <div className="h-full" onClick={clearSelection}>
      <div onClick={preventClick}>
        <div>
          <input
            ref={inputRef}
            onChange={(e) => setParticipantInput(e.target.value)}
            value={participantInput}
          />
          {action && (
            <button onClick={doAction}>
              <FontAwesomeIcon
                icon={faArrowTurnDown}
                className="rotate-90 mr-2"
              />
              {action}
            </button>
          )}
        </div>

        {participants.loading && (
          <FontAwesomeIcon
            icon={faSpinner}
            className="animate-spin-slow text-gray-300 h-8"
          />
        )}
        {participants.response && (
          <ul>
            {participants.response.map((participant: Participant) => (
              <li
                onClick={selectParticipant(participant)}
                className={
                  "flex flex-row justify-between " +
                  (participantInput.length > 0 &&
                  selectedText &&
                  participant.name.startsWith(participantInput)
                    ? "bg-blue-100 "
                    : "") +
                  (participant.id == selectedParticipant?.id
                    ? "border-blue-400 border"
                    : "")
                }
                key={participant.id}
              >
                <span>{participant.name}</span>

                <div>
                  {selectedTextIsSpeaker(selectedText) && !loading && (
                    <button onClick={mergeSpeaker(selectedText, participant)}>
                      {oneMatch &&
                        action == "Create to rename" &&
                        participant.name.startsWith(participantInput) && (
                          <>
                            {" "}
                            <span>CTRL + </span>{" "}
                            <FontAwesomeIcon
                              icon={faArrowTurnDown}
                              className="rotate-90 mr-2"
                            />{" "}
                          </>
                        )}{" "}
                      Merge
                    </button>
                  )}
                  {selectedTextIsTimeSlice(selectedText) && !loading && (
                    <button onClick={assignTo(participant)}>
                      {oneMatch &&
                        action == "Create and assign" &&
                        participant.name.startsWith(participantInput) && (
                          <>
                            {" "}
                            <span>CTRL + </span>{" "}
                            <FontAwesomeIcon
                              icon={faArrowTurnDown}
                              className="rotate-90 mr-2"
                            />{" "}
                          </>
                        )}{" "}
                      Assign
                    </button>
                  )}

                  <button onClick={deleteParticipant(participant.id)}>
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
