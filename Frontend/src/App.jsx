import { ToastProvider } from "./context/ToastContext";
import Dashboard from "./Dashboard";
import "./index.css";

export default function App() {
  return (
    <ToastProvider>
      <Dashboard />
    </ToastProvider>
  );
}
