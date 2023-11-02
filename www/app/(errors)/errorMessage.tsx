"use client";
import { useError } from "./errorContext";
import { useEffect, useState } from "react";
import * as Sentry from "@sentry/react";

const ErrorMessage: React.FC = () => {
  const { error, setError, humanMessage } = useError();
  const [isVisible, setIsVisible] = useState<boolean>(false);
  const [timeoutId, setTimeoutId] = useState<NodeJS.Timeout>();

  // Setup Shortcuts
  useEffect(() => {
    const handleKeyPress = (event: KeyboardEvent) => {
      switch (event.key) {
        case "^":
          throw new Error("Unhandled Exception thrown by '^' shortcut");
        case "$":
          setError(
            new Error("Unhandled Exception thrown by '$' shortcut"),
            "You did this to yourself",
          );
      }
    };

    document.addEventListener("keydown", handleKeyPress);
    return () => document.removeEventListener("keydown", handleKeyPress);
  }, []);

  useEffect(() => {
    if (error) {
      if (humanMessage) {
        setIsVisible(true);
        Sentry.captureException(Error(humanMessage, { cause: error }));
      } else {
        Sentry.captureException(error);
      }

      console.error("Error", error);
    }
  }, [error]);

  useEffect(() => {
    if (isVisible) {
      setTimeoutId(
        setTimeout(() => {
          setIsVisible(false);
          setTimeoutId(undefined);
        }, 30000),
      );
    }
    if (!isVisible && timeoutId) {
      clearTimeout(timeoutId);
    }
  }, [isVisible]);

  if (!isVisible || !humanMessage) return null;

  return (
    <button
      onClick={() => {
        setIsVisible(false);
        setIsVisible(false);
      }}
      className="max-w-xs z-50 fixed bottom-5 right-5 md:bottom-10 md:right-10 border-solid bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded transition-opacity duration-300 ease-out opacity-100 hover:opacity-80 focus-visible:opacity-80 cursor-pointer transform hover:scale-105 focus-visible:scale-105"
      role="alert"
    >
      <span className="block sm:inline">{humanMessage}</span>
    </button>
  );
};

export default ErrorMessage;
