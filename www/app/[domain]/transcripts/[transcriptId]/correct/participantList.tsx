import { faArrowTurnDown, faSpinner } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { useEffect, useRef, useState } from "react";
import { Participant } from "../../../../api";
import getApi from "../../../../lib/getApi";
import { UseParticipants } from "../../useParticipants";
import { unescapeLeadingUnderscores } from "typescript";

type ParticipantList = {
  participants: UseParticipants;
  transcriptId: string;
  selectedTime: any;
  topicWithWords: any;
  stateSelectedSpeaker: any;
};

const ParticipantList = ({
  transcriptId,
  participants,
  selectedTime,
  topicWithWords,
  stateSelectedSpeaker,
}: ParticipantList) => {
  const api = getApi();

  const [loading, setLoading] = useState(false);
  const [participantInput, setParticipantInput] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const [selectedSpeaker, setSelectedSpeaker] = stateSelectedSpeaker;
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
      if (selectedSpeaker !== undefined) {
        inputRef.current?.focus();
        const participant = participants.response.find(
          (p) => p.speaker == selectedSpeaker,
        );
        if (participant) {
          setParticipantInput(participant.name);
          inputRef.current?.focus();
          setAction("Rename");
        } else {
          setParticipantInput("");
          inputRef.current?.focus();
          setAction("Create to rename");
        }
      }
      if (selectedTime) {
        setParticipantInput("");
        inputRef.current?.focus();
        setAction("Create and assign");
      }
    }
  }, [selectedTime, selectedSpeaker]);

  useEffect(() => {
    if (participants.response && action == "Create and assign") {
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
  }, [participantInput]);

  useEffect(() => {
    document.onkeyup = (e) => {
      if (e.key === "Enter" && e.ctrlKey) {
        if (oneMatch) {
          assignTo(oneMatch)();
          setOneMatch(undefined);
          setParticipantInput("");
        }
      }
    };
  });

  const doAction = (e) => {
    if (!participants.response) return;
    if (action == "Rename") {
      const participant = participants.response.find(
        (p) => p.speaker == selectedSpeaker,
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
    } else if (action == "Create to rename") {
      setLoading(true);
      console.log(participantInput, selectedSpeaker);
      api
        ?.v1TranscriptAddParticipant({
          createParticipant: {
            name: participantInput,
            speaker: selectedSpeaker,
          },
          transcriptId,
        })
        .then(() => {
          participants.refetch();
        });
    } else if (action == "Create and assign") {
      setLoading(true);
      api
        ?.v1TranscriptAddParticipant({
          createParticipant: {
            name: participantInput,
            speaker: Math.floor(Math.random() * 100 + 10),
          },
          transcriptId,
        })
        .then((participant) => {
          assignTo(participant)();
          participants.refetch();
        });
    }
    e.preventDefault();
    console.log(e);
    console.log(action);
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
      if (selectedTime?.start == undefined || selectedTime?.end == undefined)
        return;
      api
        ?.v1TranscriptAssignSpeaker({
          speakerAssignment: {
            speaker: participant.speaker,
            timestampFrom: selectedTime.start,
            timestampTo: selectedTime.end,
          },
          transcriptId,
        })
        .then(() => {
          topicWithWords.refetch();
        });
    };

  const selectParticipant = (participant) => (e) => {
    console.log(participant, e);
    setSelectedSpeaker(participant.speaker);
  };
  return (
    <>
      <form onSubmit={doAction}>
        <input
          ref={inputRef}
          onChange={(e) => setParticipantInput(e.target.value)}
          value={participantInput}
        />
        <button type="submit">
          <FontAwesomeIcon icon={faArrowTurnDown} className="rotate-90 mr-2" />
          {action}
        </button>
      </form>

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
                selectedTime &&
                participant.name.startsWith(participantInput)
                  ? "bg-blue-100 "
                  : "") +
                (participant.speaker == selectedSpeaker
                  ? "border-blue-400 border"
                  : "")
              }
              key={participant.id}
            >
              <span>{participant.name}</span>

              <div>
                {selectedTime && !loading && (
                  <button onClick={assignTo(participant)}>
                    {oneMatch &&
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
    </>
  );
};

export default ParticipantList;
