/**
 * ExportPanel — PDF export only via backend.
 */

import { useState } from "react";
import { downloadPDF } from "../api/api";
import { useToast } from "../context/ToastContext";

function ExportPanel({ timetable }) {
    const { showToast } = useToast();
    const [loading, setLoading] = useState(false);

    const id = timetable?.id || timetable?._id;
    if (!timetable || !id) return null;

    const handlePdf = async () => {
        setLoading(true);
        try {
            await downloadPDF(id);
            showToast("PDF download started", "success");
        } catch (err) {
            showToast(err.response?.data?.detail || err.message || "Export failed", "error");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="panel export-panel">
            <div className="panel-title">💾 Export Timetable</div>
            <button
                className="btn-primary full-width"
                onClick={handlePdf}
                disabled={loading}
                title="Download as PDF"
            >
                {loading ? "Exporting…" : "📄 Download PDF"}
            </button>
        </div>
    );
}

export default ExportPanel;
