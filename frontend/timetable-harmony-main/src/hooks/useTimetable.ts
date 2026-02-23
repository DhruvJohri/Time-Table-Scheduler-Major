import { useState, useCallback } from "react";
import {
  TimetableEntry,
  generateTimetable,
  getSectionTimetable,
  clearTimetable,
  exportPdf,
} from "@/api/timetableApi";
import { toast } from "@/hooks/use-toast";

export function useTimetable() {
  const [entries, setEntries] = useState<TimetableEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);

  const generate = useCallback(
    async (branch: string, year: number, section: string) => {
      setGenerating(true);
      try {
        const res = await generateTimetable();
        if (res.status === "success") {
          toast({ title: "Success", description: res.message || "Timetable generated successfully." });
        } else if (res.status === "partial") {
          toast({
            title: "Partial Generation",
            description: `Some subjects could not be allocated: ${res.unallocated?.join(", ")}`,
            variant: "destructive",
          });
        }
        await fetchSection(branch, year, section);
      } catch (err: any) {
        toast({
          title: "Error",
          description: err?.response?.data?.detail || "Failed to generate timetable.",
          variant: "destructive",
        });
      } finally {
        setGenerating(false);
      }
    },
    []
  );

  const fetchSection = useCallback(
    async (branch: string, year: number, section: string) => {
      setLoading(true);
      try {
        const data = await getSectionTimetable(branch, year, section);
        setEntries(data);
      } catch (err: any) {
        toast({
          title: "Error",
          description: err?.response?.data?.detail || "Failed to fetch timetable.",
          variant: "destructive",
        });
        setEntries([]);
      } finally {
        setLoading(false);
      }
    },
    []
  );

  const reset = useCallback(async () => {
    setLoading(true);
    try {
      await clearTimetable();
      setEntries([]);
      toast({ title: "Reset", description: "Timetable has been cleared." });
    } catch (err: any) {
      toast({
        title: "Error",
        description: err?.response?.data?.detail || "Failed to clear timetable.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  }, []);

  const downloadPdf = useCallback(
    async (branch: string, year: number, section: string) => {
      setLoading(true);
      try {
        await exportPdf(branch, year, section);
        toast({ title: "Exported", description: "PDF downloaded successfully." });
      } catch (err: any) {
        toast({
          title: "Error",
          description: err?.response?.data?.detail || "Failed to export PDF.",
          variant: "destructive",
        });
      } finally {
        setLoading(false);
      }
    },
    []
  );

  return { entries, loading, generating, generate, fetchSection, reset, downloadPdf };
}
