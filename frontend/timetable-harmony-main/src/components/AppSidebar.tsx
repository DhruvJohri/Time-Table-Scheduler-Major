import React from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  CalendarDays,
  LayoutDashboard,
  Upload,
  FileUp,
  Trash2,
  FileDown,
} from "lucide-react";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import { NavLink } from "@/components/NavLink";

const navItems = [
  { title: "Dashboard", url: "/", icon: LayoutDashboard },
  { title: "View Timetable", url: "/timetable", icon: CalendarDays },
  { title: "Upload Master", url: "/upload/master", icon: Upload },
  { title: "Upload Assignment", url: "/upload/assignment", icon: FileUp },
];

const AppSidebar: React.FC = () => {
  return (
    <Sidebar className="w-60 border-r border-sidebar-border">
      <SidebarContent>
        <div className="p-4 pb-2">
          <h1 className="text-lg font-bold text-sidebar-foreground flex items-center gap-2">
            <CalendarDays className="h-5 w-5 text-sidebar-primary" />
            TimeTable Pro
          </h1>
          <p className="text-xs text-sidebar-foreground/60 mt-0.5">Academic Scheduler</p>
        </div>

        <SidebarGroup>
          <SidebarGroupLabel className="text-sidebar-foreground/50 text-[10px] uppercase tracking-wider">
            Navigation
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {navItems.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton asChild>
                    <NavLink
                      to={item.url}
                      end={item.url === "/"}
                      className="flex items-center gap-2 px-3 py-2 rounded-md text-sm text-sidebar-foreground/80 hover:bg-sidebar-accent hover:text-sidebar-foreground transition-colors"
                      activeClassName="bg-sidebar-accent text-sidebar-primary font-medium"
                    >
                      <item.icon className="h-4 w-4" />
                      <span>{item.title}</span>
                    </NavLink>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
    </Sidebar>
  );
};

export default AppSidebar;
