import React, { useCallback, useState, useRef } from "react";
import { Upload, FileSpreadsheet, X, Loader2, CheckCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "@/hooks/use-toast";

interface Props {
  label: string;
  onUpload: (file: File) => Promise<any>;
}

const FileUpload: React.FC<Props> = ({ label, onUpload }) => {
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [success, setSuccess] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const validateFile = (f: File) => {
    if (!f.name.endsWith(".xlsx")) {
      toast({ title: "Invalid File", description: "Only .xlsx files are allowed.", variant: "destructive" });
      return false;
    }
    return true;
  };

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f && validateFile(f)) setFile(f);
  }, []);

  const handleSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f && validateFile(f)) setFile(f);
  };

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setSuccess(false);
    try {
      await onUpload(file);
      setSuccess(true);
      toast({ title: "Uploaded", description: `${file.name} uploaded successfully.` });
      setTimeout(() => {
        setFile(null);
        setSuccess(false);
      }, 2000);
    } catch (err: any) {
      toast({
        title: "Upload Failed",
        description: err?.response?.data?.detail || "Could not upload file.",
        variant: "destructive",
      });
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-foreground">{label}</h3>
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        className={`relative cursor-pointer rounded-lg border-2 border-dashed p-8 text-center transition-colors ${
          dragging
            ? "border-primary bg-primary/5"
            : "border-border hover:border-primary/50 hover:bg-muted/50"
        }`}
      >
        <input ref={inputRef} type="file" accept=".xlsx" className="hidden" onChange={handleSelect} />
        <Upload className="mx-auto h-8 w-8 text-muted-foreground mb-2" />
        <p className="text-sm text-muted-foreground">
          Drag & drop <span className="font-medium text-foreground">.xlsx</span> file here or click to browse
        </p>
      </div>

      {file && (
        <div className="flex items-center gap-3 rounded-md border border-border bg-muted/50 p-3 animate-fade-in">
          <FileSpreadsheet className="h-5 w-5 text-primary shrink-0" />
          <span className="flex-1 text-sm text-foreground truncate">{file.name}</span>
          {success ? (
            <CheckCircle className="h-5 w-5 text-tt-lab shrink-0" />
          ) : (
            <button onClick={() => setFile(null)} className="text-muted-foreground hover:text-destructive">
              <X className="h-4 w-4" />
            </button>
          )}
        </div>
      )}

      <Button onClick={handleUpload} disabled={!file || uploading} className="w-full">
        {uploading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
        {uploading ? "Uploading..." : "Upload"}
      </Button>
    </div>
  );
};

export default FileUpload;
