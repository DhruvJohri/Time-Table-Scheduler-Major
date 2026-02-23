import { useState } from "react";
import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { SidebarProvider } from "@/components/ui/sidebar";
import AppSidebar from "@/components/AppSidebar";
import TopBar from "@/components/TopBar";
import Dashboard from "@/pages/Dashboard";
import TimetablePage from "@/pages/TimetablePage";
import UploadMasterPage from "@/pages/UploadMasterPage";
import UploadAssignmentPage from "@/pages/UploadAssignmentPage";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

const AppLayout = () => {
  const [branch, setBranch] = useState("CSE");
  const [year, setYear] = useState(3);
  const [section, setSection] = useState("A");

  return (
    <SidebarProvider>
      <div className="min-h-screen flex w-full">
        <AppSidebar />
        <div className="flex-1 flex flex-col min-w-0">
          <TopBar
            branch={branch}
            year={year}
            section={section}
            onBranchChange={setBranch}
            onYearChange={setYear}
            onSectionChange={setSection}
          />
          <main className="flex-1 overflow-auto">
            <Routes>
              <Route path="/" element={<Dashboard branch={branch} year={year} section={section} />} />
              <Route path="/timetable" element={<TimetablePage branch={branch} year={year} section={section} />} />
              <Route path="/upload/master" element={<UploadMasterPage />} />
              <Route path="/upload/assignment" element={<UploadAssignmentPage />} />
              <Route path="*" element={<NotFound />} />
            </Routes>
          </main>
        </div>
      </div>
    </SidebarProvider>
  );
};

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <AppLayout />
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
