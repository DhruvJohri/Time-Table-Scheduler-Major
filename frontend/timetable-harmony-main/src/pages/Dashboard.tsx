import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CalendarDays, Zap, Trash2, FileDown, Loader2 } from "lucide-react";
import { useTimetable } from "@/hooks/useTimetable";

interface Props {
  branch: string;
  year: number;
  section: string;
}

const Dashboard: React.FC<Props> = ({ branch, year, section }) => {
  const { generate, reset, downloadPdf, generating, loading } = useTimetable();

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6 animate-fade-in">
      <div>
        <h2 className="text-2xl font-bold text-foreground">Dashboard</h2>
        <p className="text-sm text-muted-foreground mt-1">
          Manage timetable for <span className="font-medium text-foreground">{branch} — Year {year} — Section {section}</span>
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Card className="border-border">
          <CardHeader className="pb-2">
            <CardTitle className="text-base flex items-center gap-2">
              <Zap className="h-4 w-4 text-primary" />
              Generate Timetable
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground mb-3">
              Generate a new timetable using the backend scheduling engine.
            </p>
            <Button
              onClick={() => generate(branch, year, section)}
              disabled={generating}
              className="w-full"
            >
              {generating ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Zap className="mr-2 h-4 w-4" />}
              {generating ? "Generating..." : "Generate"}
            </Button>
          </CardContent>
        </Card>

        <Card className="border-border">
          <CardHeader className="pb-2">
            <CardTitle className="text-base flex items-center gap-2">
              <FileDown className="h-4 w-4 text-primary" />
              Export PDF
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground mb-3">
              Download the timetable as a PDF file.
            </p>
            <Button
              variant="secondary"
              onClick={() => downloadPdf(branch, year, section)}
              disabled={loading}
              className="w-full"
            >
              {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <FileDown className="mr-2 h-4 w-4" />}
              Export
            </Button>
          </CardContent>
        </Card>

        <Card className="border-border sm:col-span-2">
          <CardHeader className="pb-2">
            <CardTitle className="text-base flex items-center gap-2 text-destructive">
              <Trash2 className="h-4 w-4" />
              Reset Timetable
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground mb-3">
              Clear all generated timetable data. This action cannot be undone.
            </p>
            <Button
              variant="destructive"
              onClick={reset}
              disabled={loading}
              className="w-full"
            >
              {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Trash2 className="mr-2 h-4 w-4" />}
              Reset Timetable
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default Dashboard;
