"use client";
import React, { useState } from "react";

import { GetTranscript } from "../../api";
import { Title } from "../../lib/textComponents";
import Pagination from "./pagination";
import Link from "next/link";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faCheck,
  faGear,
  faMicrophone,
  faStar,
  faTrash,
  faX,
} from "@fortawesome/free-solid-svg-icons";
import useTranscriptList from "../transcripts/useTranscriptList";
import { formatTime } from "../../lib/time";
import getApi from "../../api";
import { useError } from "../../(errors)/errorContext";

export default function TranscriptBrowser() {
  const [page, setPage] = useState<number>(1);
  const { loading, response, refetch } = useTranscriptList(page);
  const [transcriptToDeleteId, setTranscriptToDeleteId] = useState("");
  const [deletionLoading, setDeletionLoading] = useState(false);
  const [deletedItems, setDeletedItems] = useState<string[]>([]);
  const api = getApi();
  const { setError } = useError();

  if (loading && !response)
    return (
      <div className="h-full flex flex-col items-center justify-center">
        <FontAwesomeIcon
          icon={faGear}
          className="animate-spin-slow h-14 w-14 md:h-20 md:w-20 text-gray-400"
        />
      </div>
    );

  if (!loading && !response)
    return (
      <div className="text-gray-500">
        No transcripts found, but you can&nbsp;
        <Link href="/transcripts/new" className="underline">
          record a meeting
        </Link>
        &nbsp;to get started.
      </div>
    );

  const handleDelete =
    (id: string) => (e: React.MouseEvent<HTMLButtonElement>) => {
      e.stopPropagation();
      e.preventDefault();
      setTranscriptToDeleteId(id);
    };

  const deleteTranscript = () => (e: React.MouseEvent<HTMLButtonElement>) => {
    e.stopPropagation();
    e.preventDefault();
    if (!deletionLoading) {
      api
        ?.v1TranscriptDelete({ transcriptId: transcriptToDeleteId })
        .then(() => {
          setDeletionLoading(false);
          setDeletedItems([...deletedItems, transcriptToDeleteId]);
          setTranscriptToDeleteId("");
          refetch();
        })
        .catch((err) => {
          setDeletionLoading(false);
          setError(err, "There was an error deleting the transcript");
        });
    }
  };
  const cancelDelete = (e: React.MouseEvent<HTMLButtonElement>) => {
    e.stopPropagation();
    e.preventDefault();
    setTranscriptToDeleteId("");
  };

  return (
    <div className="w-full flex flex-col items-center justify-center flex-grow">
      <div className="max-w-5xl h-full">
        <div className="flex flex-row gap-2 items-center">
          <Title className="mb-5 mt-5 flex-1">Past transcripts</Title>
          <Pagination
            page={page}
            setPage={setPage}
            total={response?.total || 0}
            size={response?.size || 0}
          />
        </div>
        <div className="grid grid-cols-1 gap-2 lg:gap-4 h-full">
          {response?.items
            .filter((item) => !deletedItems.includes(item.id))
            .map((item: GetTranscript) => (
              <Link
                key={item.id}
                href={`/transcripts/${item.id}`}
                className="flex flex-col bg-blue-400/20 rounded-lg md:rounded-xl p-2 md:px-4"
              >
                <div className="flex flex-col">
                  <div className="flex flex-row gap-2 items-start">
                    <h2 className="text-1xl font-semibold flex-1">
                      {item.title || item.name}
                    </h2>

                    {item.locked && (
                      <div className="inline-block bg-red-500 text-white px-2 py-1 rounded-full text-xs font-semibold">
                        Locked
                      </div>
                    )}

                    {item.status == "ended" && (
                      <FontAwesomeIcon
                        icon={faCheck}
                        className="mt-1 text-green-500"
                      />
                    )}
                    {item.status == "error" && (
                      <FontAwesomeIcon
                        icon={faX}
                        className="mt-1 text-red-500"
                      />
                    )}
                    {item.status == "idle" && (
                      <FontAwesomeIcon
                        icon={faStar}
                        className="mt-1 text-yellow-500"
                      />
                    )}
                    {item.status == "processing" && (
                      <FontAwesomeIcon
                        icon={faGear}
                        className="mt-1 text-grey-500"
                      />
                    )}
                    {item.status == "recording" && (
                      <FontAwesomeIcon
                        icon={faMicrophone}
                        className="mt-1 text-blue-500"
                      />
                    )}

                    {item.sourceLanguage && (
                      <div className="inline-block bg-blue-500 text-white px-2 py-1 rounded-full text-xs font-semibold">
                        {item.sourceLanguage}
                      </div>
                    )}
                  </div>
                  <div className="flex flex-row gap-2 items-start">
                    <div className="text-xs text-gray-700 flex-1">
                      {new Date(item.createdAt).toLocaleDateString("en-US")}
                      {"\u00A0"}-{"\u00A0"}
                      {formatTime(Math.floor(item.duration))}
                      <div className="text-sm">{item.shortSummary}</div>
                    </div>
                    {item.status !== "ended" && (
                      <button
                        className="self-end p-2"
                        disabled={deletionLoading}
                        onClick={handleDelete(item.id)}
                      >
                        <FontAwesomeIcon icon={faTrash}></FontAwesomeIcon>
                      </button>
                    )}
                    <dialog open={transcriptToDeleteId == item.id}>
                      <p>Are you sure you want to delete {item.title} ?</p>
                      <p>This action is not reversible.</p>
                      <button onClick={cancelDelete}>Cancel</button>
                      <button onClick={deleteTranscript()}>Confirm</button>
                    </dialog>
                  </div>
                </div>
              </Link>
            ))}
        </div>
      </div>
    </div>
  );
}
