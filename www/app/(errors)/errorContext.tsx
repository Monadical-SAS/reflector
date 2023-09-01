"use client";
import React, { createContext, useContext, useState } from "react";

interface ErrorContextProps {
  error: Error | null;
  setError: React.Dispatch<React.SetStateAction<Error | null>>;
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

  return (
    <ErrorContext.Provider value={{ error, setError }}>
      {children}
    </ErrorContext.Provider>
  );
};
