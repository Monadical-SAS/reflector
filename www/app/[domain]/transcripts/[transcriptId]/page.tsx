"use client";
import Modal from "../modal";
import useTranscript from "../useTranscript";
import useTopics from "../useTopics";
import useWaveform from "../useWaveform";
import useMp3 from "../useMp3";
import { TopicList } from "../topicList";
import Recorder from "../recorder";
import { Topic } from "../webSocketTypes";
import React, { useState } from "react";
import "../../../styles/button.css";
import FinalSummary from "../finalSummary";
import ShareLink from "../shareLink";
import QRCode from "react-qr-code";
import TranscriptTitle from "../transcriptTitle";
import ShareModal from "./shareModal";

type TranscriptDetails = {
  params: {
    transcriptId: string;
  };
};

const protectedPath = true;

export default function TranscriptDetails(details: TranscriptDetails) {
  const transcriptId = details.params.transcriptId;

  const transcript = useTranscript(protectedPath, transcriptId);
  const topics = useTopics(protectedPath, transcriptId);
  const waveform = useWaveform(protectedPath, transcriptId);
  const useActiveTopic = useState<Topic | null>(null);
  const mp3 = useMp3(protectedPath, transcriptId);
  const [showModal, setShowModal] = useState(false);

  if (transcript?.error /** || topics?.error || waveform?.error **/) {
    return (
      <Modal
        title="Transcription Not Found"
        text="A trascription with this ID does not exist."
      />
    );
  }

  const fullTranscript =
    topics.topics
      ?.map((topic) => topic.transcript)
      .join("\n\n")
      .replace(/ +/g, " ")
      .trim() || "";

  if (
    (transcript?.response?.longSummary === null || true) &&
    transcript &&
    transcript.response
  ) {
    transcript.response.longSummary = `
**Meeting Summary:**

**Date:** November 21, 2023
**Attendees:** Alice Johnson, Bob Smith, Carlos Gomez, Dana Lee
**Agenda Items:**

1. **Project Alpha Update:**
   - Discussed current progress and minor setbacks.
   - Agreed on extending the deadline by two weeks.
   - Assigned new tasks to team members.

2. **Budget Review for Quarter 4:**
   - Reviewed financial performance.
   - Identified areas of overspending and discussed cost-cutting measures.
   - Decided to allocate additional funds to marketing.

3. **New Product Launch Strategy:**
   - Brainstormed ideas for the upcoming product launch.
   - Agreed on a digital-first marketing approach.
   - Set a tentative launch date for January 15, 2024.

**Key Decisions:**
- Extend Project Alpha's deadline to allow for quality enhancement.
- Implement cost-saving strategies in non-essential departments.
- Proceed with the digital marketing plan for the new product launch.

**Action Items:**
- Alice to coordinate with the marketing team for the new campaign.
- Bob to oversee the budget adjustments and report back in one week.
- Carlos to lead the task force for Project Alpha's final phase.
- Dana to prepare a detailed report on competitor analysis for the next meeting.

**Next Meeting:**
Scheduled for December 5, 2023, to review progress and finalize the new product launch details.
`;
  }

  return (
    <>
      {!transcriptId || transcript?.loading || topics?.loading ? (
        <Modal title="Loading" text={"Loading transcript..."} />
      ) : (
        <>
          <ShareModal
            transcript={transcript.response}
            topics={topics ? topics.topics : null}
            show={showModal}
            setShow={(v) => setShowModal(v)}
            title={transcript?.response?.title}
            summary={transcript?.response?.longSummary}
            date={transcript?.response?.createdAt}
            url={window.location.href}
          />
          <div className="flex flex-col">
            {transcript?.response?.title && (
              <TranscriptTitle
                protectedPath={protectedPath}
                title={transcript.response.title}
                transcriptId={transcript.response.id}
              />
            )}
            {!waveform?.loading && (
              <Recorder
                topics={topics?.topics || []}
                useActiveTopic={useActiveTopic}
                waveform={waveform?.waveform}
                isPastMeeting={true}
                transcriptId={transcript?.response?.id}
                media={mp3?.media}
                mediaDuration={transcript?.response?.duration}
              />
            )}
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 grid-rows-2 lg:grid-rows-1 gap-2 lg:gap-4 h-full">
            <TopicList
              topics={topics?.topics || []}
              useActiveTopic={useActiveTopic}
              autoscroll={false}
            />
            <div className="w-full h-full grid grid-rows-layout-one grid-cols-1 gap-2 lg:gap-4">
              <section className=" bg-blue-400/20 rounded-lg md:rounded-xl p-2 md:px-4 h-full">
                {transcript?.response?.longSummary && (
                  <FinalSummary
                    protectedPath={protectedPath}
                    fullTranscript={fullTranscript}
                    summary={transcript?.response?.longSummary}
                    transcriptId={transcript?.response?.id}
                    openZulipModal={() => setShowModal(true)}
                  />
                )}
              </section>

              <section className="flex items-center">
                <div className="mr-4 hidden md:block h-auto">
                  <QRCode
                    value={`${location.origin}/transcripts/${details.params.transcriptId}`}
                    level="L"
                    size={98}
                  />
                </div>
                <div className="flex-grow max-w-full">
                  <ShareLink />
                </div>
              </section>
            </div>
          </div>
        </>
      )}
    </>
  );
}
