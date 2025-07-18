"use client";

// Simple toaster implementation for migration
// This is a temporary solution until we properly configure Chakra UI v3 toasts

interface ToastOptions {
  placement?: string;
  duration?: number | null;
  render: (props: { dismiss: () => void }) => React.ReactNode;
}

class ToasterClass {
  private toasts: Map<string, any> = new Map();
  private nextId = 1;

  create(options: ToastOptions): Promise<string> {
    const id = String(this.nextId++);
    this.toasts.set(id, options);

    // For now, we'll render toasts using a portal or modal
    // This is a simplified implementation
    if (typeof window !== "undefined") {
      console.log("Toast created:", id, options);

      // Auto-dismiss after duration if specified
      if (options.duration !== null) {
        setTimeout(() => {
          this.dismiss(id);
        }, options.duration || 5000);
      }
    }

    return Promise.resolve(id);
  }

  dismiss(id: string) {
    this.toasts.delete(id);
    console.log("Toast dismissed:", id);
  }

  isActive(id: string): boolean {
    return this.toasts.has(id);
  }
}

export const toaster = new ToasterClass();

// Empty Toaster component for now
export const Toaster = () => null;
