// src/context/ToastContext.jsx
import React, { createContext, useContext, useState, useCallback } from "react";

const ToastContext = createContext(null);

let idCounter = 0;

export const ToastProvider = ({ children }) => {
  const [toasts, setToasts] = useState([]);

  const removeToast = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const showToast = useCallback((message, type = "success") => {
    const id = ++idCounter;
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => removeToast(id), 3000);
  }, [removeToast]);

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      <ToastContainer toasts={toasts} />
    </ToastContext.Provider>
  );
};

export const useToast = () => useContext(ToastContext);

const ToastContainer = ({ toasts }) => (
  <div className="fixed top-4 right-4 z-[9999] flex flex-col gap-2">
    {toasts.map((toast) => (
      <div
        key={toast.id}
        className={`min-w-[220px] max-w-sm rounded-lg px-4 py-3 shadow-lg flex items-center gap-2 text-sm text-white
          transition-transform duration-200 ease-out
          ${toast.type === "error" ? "bg-red-500"
            : toast.type === "info" ? "bg-blue-500"
            : "bg-green-500"}`}
      >
        <span className="material-symbols-outlined text-base">
          {toast.type === "error"
            ? "error"
            : toast.type === "info"
            ? "info"
            : "check_circle"}
        </span>
        <span>{toast.message}</span>
      </div>
    ))}
  </div>
);
