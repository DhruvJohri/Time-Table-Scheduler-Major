import React from "react";
import FileUpload from "@/components/FileUpload";
import { uploadMasterExcel } from "@/api/uploadApi";

const UploadMasterPage: React.FC = () => (
  <div className="p-6 max-w-lg mx-auto animate-fade-in">
    <h2 className="text-2xl font-bold text-foreground mb-1">Upload Master Data</h2>
    <p className="text-sm text-muted-foreground mb-6">
      Upload the master Excel file containing subjects, faculty, and room data.
    </p>
    <FileUpload label="Master Excel (.xlsx)" onUpload={uploadMasterExcel} />
  </div>
);

export default UploadMasterPage;
