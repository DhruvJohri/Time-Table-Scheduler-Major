import axiosInstance from "./axiosInstance";

export interface TimetableEntry {
  day: string;
  period: number;
  branch: string;
  year: number;
  section: string;
  subject: string;
  subject_code: string;
  faculty: string;
  room: string;
  type: string;
}

export interface GenerateResponse {
  status: "success" | "partial";
  message?: string;
  unallocated?: string[];
}

export const generateTimetable = async (): Promise<GenerateResponse> => {
  const { data } = await axiosInstance.post("/timetable/generate", {
    force_regenerate: true,
    include_clubs: true,
    fill_extracurricular: true,
  });
  return {
    status: data?.success ? "success" : "partial",
    message: data?.message,
    unallocated: data?.failed_subjects ?? [],
  };
};

export const getFullTimetable = async (): Promise<TimetableEntry[]> => {
  const { data } = await axiosInstance.get<TimetableEntry[]>("/timetable");
  return data;
};

export const getSectionTimetable = async (
  branch: string,
  year: number,
  section: string
): Promise<TimetableEntry[]> => {
  const { data } = await axiosInstance.get(
    `/timetable/${branch}/${year}/${section}`
  );

  const dayMap: Record<string, string> = {
    MONDAY: "Monday",
    TUESDAY: "Tuesday",
    WEDNESDAY: "Wednesday",
    THURSDAY: "Thursday",
    FRIDAY: "Friday",
    SATURDAY: "Saturday",
  };

  const entries = Array.isArray(data?.entries) ? data.entries : [];

  return entries.map((entry: any) => ({
    day: dayMap[entry.day] ?? entry.day,
    period: entry.period,
    branch,
    year,
    section,
    subject: entry.subject_name ?? entry.subject ?? "",
    subject_code: entry.subject ?? "",
    faculty: entry.faculty ?? "",
    room: entry.classroom ?? entry.labroom ?? "",
    type: entry.type ?? "",
  }));
};

export const clearTimetable = async (): Promise<void> => {
  await axiosInstance.delete("/timetable/clear");
};

export const exportPdf = async (
  branch: string,
  year: number,
  section: string
): Promise<void> => {
  const response = await axiosInstance.get(
    `/timetable/export/${branch}/${year}/${section}`,
    { responseType: "blob" }
  );
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement("a");
  link.href = url;
  link.setAttribute("download", `timetable_${branch}_${year}_${section}.pdf`);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};
