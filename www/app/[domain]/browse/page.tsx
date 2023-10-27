"use client";
import React, { useState, useEffect } from "react";
import getApi from "../../lib/getApi";
import {
  PageGetTranscript,
  GetTranscript,
  GetTranscriptFromJSON,
} from "../../api";
import { Title } from "../../lib/textComponents";
import Pagination from "./pagination";
import Link from "next/link";
import { useFiefIsAuthenticated } from "@fief/fief/nextjs/react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faGear } from "@fortawesome/free-solid-svg-icons";
import { featureEnabled } from "../domainContext";
import router from "next/router";

export default function TranscriptBrowser() {
  const api = getApi();
  const [results, setResults] = useState<PageGetTranscript | null>(null);
  const [page, setPage] = useState<number>(1);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const isAuthenticated = useFiefIsAuthenticated();
  const browseEnabled = featureEnabled("browse");

  useEffect(() => {
    if (!isAuthenticated) return;
    setIsLoading(true);
    api
      .v1TranscriptsList({ page })
      .then((response) => {
        // issue with API layer, conversion for items is not happening
        response.items = response.items.map((item) =>
          GetTranscriptFromJSON(item),
        );
        setResults(response);
        setIsLoading(false);
      })
      .catch(() => {
        setResults(null);
        setIsLoading(false);
      });
  }, [page, isAuthenticated]);

  return (
    <div>
      {/*
      <div className="flex flex-row gap-2">
        <input className="text-sm p-2 w-80 ring-1 ring-slate-900/10 shadow-sm rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 caret-blue-500" placeholder="Search" />
      </div>
      */}

      <div className="flex flex-row gap-2 items-center">
        <Title className="mb-5 mt-5 flex-1">Past transcripts</Title>
        <Pagination
          page={page}
          setPage={setPage}
          total={results?.total || 0}
          size={results?.size || 0}
        />
      </div>

      {isLoading && (
        <div className="full-screen flex flex-col items-center justify-center">
          <FontAwesomeIcon
            icon={faGear}
            className="animate-spin-slow h-14 w-14 md:h-20 md:w-20"
          />
        </div>
      )}
      {!isLoading && !results ? (
        <div className="text-gray-500">
          No transcripts found, but you can&nbsp;
          <Link href="/transcripts/new" className="underline">
            record a meeting
          </Link>
          &nbsp;to get started.
        </div>
      ) : (
        <></>
      )}
      <div /** center and max 900px wide */ className="mx-auto max-w-[900px]">
        <div className="grid grid-cols-1 gap-2 lg:gap-4 h-full">
          {results?.items.map((item: GetTranscript) => (
            <div
              key={item.id}
              className="flex flex-col bg-blue-400/20 rounded-lg md:rounded-xl p-2 md:px-4"
            >
              <div className="flex flex-col">
                <div className="flex flex-row gap-2 items-start">
                  <Link
                    href={`/transcripts/${item.id}`}
                    className="text-1xl font-semibold flex-1 pl-0 hover:underline focus-within:underline underline-offset-2 decoration-[.5px] font-light px-2"
                  >
                    {item.title || item.name}
                  </Link>

                  {item.locked ? (
                    <div className="inline-block bg-red-500 text-white px-2 py-1 rounded-full text-xs font-semibold">
                      Locked
                    </div>
                  ) : (
                    <></>
                  )}

                  {item.sourceLanguage ? (
                    <div className="inline-block bg-blue-500 text-white px-2 py-1 rounded-full text-xs font-semibold">
                      {item.sourceLanguage}
                    </div>
                  ) : (
                    <></>
                  )}
                </div>
                <div className="text-xs text-gray-700">
                  {new Date(item.createdAt).toLocaleDateString("en-US")}
                </div>
                <div className="text-sm">{item.shortSummary}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
