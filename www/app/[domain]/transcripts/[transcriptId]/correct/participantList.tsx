import { faSpinner } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { useEffect, useRef, useState } from "react";
import { Participant } from "../../../../api";
import getApi from "../../../../lib/getApi";

const ParticipantList = ({
  transcriptId,
  participants,
  selectedTime,
  topicWithWords,
}) => {
  const api = getApi();

  const [loading, setLoading] = useState(false);
  const [participantInput, setParticipantInput] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const createParticipant = () => {
    if (!loading) {
      setLoading(true);
      api
        ?.v1TranscriptAddParticipant({
          createParticipant: { name: participantInput, speaker: 99 },
          transcriptId,
        })
        .then((participant) => {
          participants.refetch();
          assignTo(participant)();
        });
    }
  };

  useEffect(() => {
    if (loading) {
      setLoading(false);
    }
  }, [participants.loading]);

  useEffect(() => {
    if (selectedTime) {
      inputRef.current?.focus();
    }
  }, [selectedTime]);

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
  return (
    <>
      <input
        ref={inputRef}
        onChange={(e) => setParticipantInput(e.target.value)}
      />
      <button onClick={createParticipant}>Create</button>
      {participants.loading && (
        <FontAwesomeIcon
          icon={faSpinner}
          className="animate-spin-slow text-gray-300 h-8"
        />
      )}
      {participants.response && (
        <ul>
          {participants.response.map((participant: Participant) => (
            <li className="flex flex-row justify-between" key={participant.id}>
              <span>{participant.name}</span>
              <div>
                <button
                  className={
                    selectedTime && !loading ? "bg-blue-400" : "bg-gray-400"
                  }
                  onClick={assignTo(participant)}
                >
                  Assign
                </button>
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
