"use client";
import React, { createContext, useContext, useState } from "react";

interface ErrorContextProps {
  error: Error | null;
  humanMessage?: string;
  setError: (error: Error, humanMessage?: string) => void;
}

const ErrorContext = createContext<ErrorContextProps | undefined>(undefined);

export const useError = () => {
  const context = useContext(ErrorContext);
  if (!context) {
    throw new Error("useError must be used within an ErrorProvider");
  }
  return context;
};

interface ErrorProviderProps {
  children: React.ReactNode;
}

export const ErrorProvider: React.FC<ErrorProviderProps> = ({ children }) => {
  const [error, setError] = useState<Error | null>(null);
  const [humanMessage, setHumanMessage] = useState<string | undefined>();

  const declareError = (error, humanMessage?) => {
    setError(error);
    setHumanMessage(humanMessage);
    console.log(error.message, { ...error });
    //TODO ignore not found in request errors (in useTopics, useTranscript...)
    // if (error.name == ResponseError && error.response.status == 404)
  };
  return (
    <ErrorContext.Provider
      value={{ error, setError: declareError, humanMessage }}
    >
      {children}
    </ErrorContext.Provider>
  );
};
