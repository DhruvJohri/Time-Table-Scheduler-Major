import React from "react";
import { Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { SidebarTrigger } from "@/components/ui/sidebar";

const BRANCHES = ["CSE", "ECE", "EEE", "ME", "CE", "IT"];
const YEARS = [1, 2, 3, 4];
const SECTIONS = ["A", "B", "C", "D"];

interface Props {
  branch: string;
  year: number;
  section: string;
  onBranchChange: (v: string) => void;
  onYearChange: (v: number) => void;
  onSectionChange: (v: string) => void;
}

const TopBar: React.FC<Props> = ({
  branch,
  year,
  section,
  onBranchChange,
  onYearChange,
  onSectionChange,
}) => {
  const [dark, setDark] = React.useState(false);

  const toggleTheme = () => {
    setDark((d) => {
      const next = !d;
      document.documentElement.classList.toggle("dark", next);
      return next;
    });
  };

  return (
    <header className="sticky top-0 z-30 flex items-center gap-3 border-b border-border bg-card px-4 py-2.5">
      <SidebarTrigger className="mr-1" />

      <div className="flex items-center gap-2 flex-1 flex-wrap">
        <Select value={branch} onValueChange={onBranchChange}>
          <SelectTrigger className="w-[110px] h-8 text-xs">
            <SelectValue placeholder="Branch" />
          </SelectTrigger>
          <SelectContent>
            {BRANCHES.map((b) => (
              <SelectItem key={b} value={b}>{b}</SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={String(year)} onValueChange={(v) => onYearChange(Number(v))}>
          <SelectTrigger className="w-[90px] h-8 text-xs">
            <SelectValue placeholder="Year" />
          </SelectTrigger>
          <SelectContent>
            {YEARS.map((y) => (
              <SelectItem key={y} value={String(y)}>Year {y}</SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={section} onValueChange={onSectionChange}>
          <SelectTrigger className="w-[90px] h-8 text-xs">
            <SelectValue placeholder="Section" />
          </SelectTrigger>
          <SelectContent>
            {SECTIONS.map((s) => (
              <SelectItem key={s} value={s}>Section {s}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <Button variant="ghost" size="icon" className="h-8 w-8" onClick={toggleTheme}>
        {dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
      </Button>
    </header>
  );
};

export default TopBar;
