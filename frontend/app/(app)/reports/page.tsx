"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Client, api, getToken } from "@/lib/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function ReportsPage() {
  const [clients, setClients] = useState<Client[]>([]);

  useEffect(() => {
    api<Client[]>("/api/v1/clients").then(setClients);
  }, []);

  async function download(clientId: string, type: "pdf" | "excel") {
    const response = await fetch(`${API_URL}/api/v1/reports/${clientId}/${type}`, {
      headers: { Authorization: `Bearer ${getToken()}` }
    });
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = type === "pdf" ? "tax-report.pdf" : "tax-summary.xlsx";
    anchor.click();
    URL.revokeObjectURL(url);
  }

  return (
    <AppShell>
      <Card>
        <CardHeader><CardTitle>Downloadable Reports</CardTitle></CardHeader>
        <CardContent className="grid gap-3">
          {clients.map((client) => (
            <div key={client.id} className="flex items-center justify-between rounded-md border p-4">
              <div><strong>{client.full_name}</strong><p className="text-sm text-muted">{client.pan}</p></div>
              <div className="flex gap-2">
                <Button onClick={() => download(client.id, "pdf")}>PDF</Button>
                <Button variant="outline" onClick={() => download(client.id, "excel")}>Excel</Button>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </AppShell>
  );
}
