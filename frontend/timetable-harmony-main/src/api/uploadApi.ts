import axiosInstance from "./axiosInstance";

export const uploadMasterExcel = async (file: File) => {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await axiosInstance.post("/upload/master", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
};

export const uploadAssignmentExcel = async (file: File) => {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await axiosInstance.post("/upload/assignment", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
};
