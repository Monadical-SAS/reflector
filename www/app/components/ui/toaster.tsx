"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
} from "react";
import { createPortal } from "react-dom";
import { Box } from "@chakra-ui/react";

interface ToastOptions {
  placement?: string;
  duration?: number | null;
  render: (props: { dismiss: () => void }) => React.ReactNode;
}

interface Toast extends ToastOptions {
  id: string;
}

interface ToasterContextType {
  toasts: Toast[];
  addToast: (options: ToastOptions) => string;
  removeToast: (id: string) => void;
}

const ToasterContext = createContext<ToasterContextType | null>(null);

export const ToasterProvider = ({
  children,
}: {
  children: React.ReactNode;
}) => {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const addToast = useCallback((options: ToastOptions) => {
    const id = String(Date.now() + Math.random());
    setToasts((prev) => [...prev, { ...options, id }]);

    if (options.duration !== null) {
      setTimeout(() => {
        removeToast(id);
      }, options.duration || 5000);
    }

    return id;
  }, []);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  }, []);

  return (
    <ToasterContext.Provider value={{ toasts, addToast, removeToast }}>
      {children}
      <ToastContainer />
    </ToasterContext.Provider>
  );
};

const ToastContainer = () => {
  const context = useContext(ToasterContext);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!context || !mounted) return null;

  return createPortal(
    <Box
      position="fixed"
      top="20px"
      left="50%"
      transform="translateX(-50%)"
      zIndex={9999}
      pointerEvents="none"
    >
      {context.toasts.map((toast) => (
        <Box key={toast.id} mb={3} pointerEvents="auto">
          {toast.render({ dismiss: () => context.removeToast(toast.id) })}
        </Box>
      ))}
    </Box>,
    document.body,
  );
};

class ToasterClass {
  private listeners: ((action: { type: string; payload: any }) => void)[] = [];
  private nextId = 1;
  private toastsMap: Map<string, boolean> = new Map();

  subscribe(listener: (action: { type: string; payload: any }) => void) {
    this.listeners.push(listener);
    return () => {
      this.listeners = this.listeners.filter((l) => l !== listener);
    };
  }

  private notify(action: { type: string; payload: any }) {
    this.listeners.forEach((listener) => listener(action));
  }

  create(options: ToastOptions): Promise<string> {
    const id = String(this.nextId++);
    this.toastsMap.set(id, true);
    this.notify({ type: "ADD_TOAST", payload: { ...options, id } });

    if (options.duration !== null) {
      setTimeout(() => {
        this.dismiss(id);
      }, options.duration || 5000);
    }

    return Promise.resolve(id);
  }

  dismiss(id: string) {
    this.toastsMap.delete(id);
    this.notify({ type: "REMOVE_TOAST", payload: id });
  }

  isActive(id: string): boolean {
    return this.toastsMap.has(id);
  }
}

export const toaster = new ToasterClass();

// Bridge component to connect the class-based API with React
export const Toaster = () => {
  const [toasts, setToasts] = useState<Toast[]>([]);

  useEffect(() => {
    const unsubscribe = toaster.subscribe((action) => {
      if (action.type === "ADD_TOAST") {
        setToasts((prev) => [...prev, action.payload]);
      } else if (action.type === "REMOVE_TOAST") {
        setToasts((prev) =>
          prev.filter((toast) => toast.id !== action.payload),
        );
      }
    });

    return unsubscribe;
  }, []);

  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) return null;

  return createPortal(
    <Box
      position="fixed"
      top="20px"
      left="50%"
      transform="translateX(-50%)"
      zIndex={9999}
      pointerEvents="none"
    >
      {toasts.map((toast) => (
        <Box key={toast.id} mb={3} pointerEvents="auto">
          {toast.render({ dismiss: () => toaster.dismiss(toast.id) })}
        </Box>
      ))}
    </Box>,
    document.body,
  );
};
