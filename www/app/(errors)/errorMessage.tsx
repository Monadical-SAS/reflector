"use client";
import { useError } from "./errorContext";
import { useEffect, useState } from "react";
import * as Sentry from "@sentry/react";

const ErrorMessage: React.FC = () => {
  const { error, setError } = useError();
  const [isVisible, setIsVisible] = useState<boolean>(false);

  useEffect(() => {
    if (error) {
      // Never set the error to visible in Scale AI branch
      //      setIsVisible(true);
      console.log("Sentry capture exception", error, typeof error);
      Sentry.captureException(error);
      console.error(error);
    }
  }, [error]);

  if (!isVisible || !error) return null;

  return (
    <div
      onClick={() => {
        setIsVisible(false);
        setError(null);
      }}
      className="max-w-xs z-50 fixed top-16 right-10 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded transition-opacity duration-300 ease-out opacity-100 hover:opacity-75 cursor-pointer transform hover:scale-105"
      role="alert"
    >
      <span className="block sm:inline">{error?.message}</span>
    </div>
  );
};

export default ErrorMessage;
