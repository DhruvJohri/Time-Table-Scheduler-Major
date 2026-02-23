import React from "react";
import FileUpload from "@/components/FileUpload";
import { uploadAssignmentExcel } from "@/api/uploadApi";

const UploadAssignmentPage: React.FC = () => (
  <div className="p-6 max-w-lg mx-auto animate-fade-in">
    <h2 className="text-2xl font-bold text-foreground mb-1">Upload Assignment Data</h2>
    <p className="text-sm text-muted-foreground mb-6">
      Upload the assignment Excel file with subject-faculty-section mappings.
    </p>
    <FileUpload label="Assignment Excel (.xlsx)" onUpload={uploadAssignmentExcel} />
  </div>
);

export default UploadAssignmentPage;
