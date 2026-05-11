"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api, Client, getToken } from "@/lib/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function UploadsPage() {
  const [clients, setClients] = useState<Client[]>([]);
  const [clientId, setClientId] = useState("");
  const [result, setResult] = useState("");

  useEffect(() => {
    api<Client[]>("/api/v1/clients").then((items) => {
      setClients(items);
      setClientId(items[0]?.id ?? "");
    });
  }, []);

  async function upload(event: React.FormEvent<HTMLFormElement>, type: "ais" | "26as") {
    event.preventDefault();
    const file = new FormData(event.currentTarget).get("file") as File;
    const body = new FormData();
    body.set("client_id", clientId);
    body.set("assessment_year", "2026-27");
    body.set("file", file);
    const response = await fetch(`${API_URL}/api/v1/uploads/${type}`, {
      method: "POST",
      headers: { Authorization: `Bearer ${getToken()}` },
      body
    });
    setResult(JSON.stringify(await response.json(), null, 2));
  }

  return (
    <AppShell>
      <div className="grid gap-6 xl:grid-cols-[420px_1fr]">
        <Card>
          <CardHeader><CardTitle>Upload Tax Files</CardTitle></CardHeader>
          <CardContent className="grid gap-5">
            <select value={clientId} onChange={(e) => setClientId(e.target.value)} className="h-10 rounded-md border bg-card px-3 text-sm">
              {clients.map((client) => <option key={client.id} value={client.id}>{client.full_name} · {client.pan}</option>)}
            </select>
            <form onSubmit={(e) => upload(e, "ais")} className="grid gap-3 rounded-md border p-4">
              <strong>AIS PDF / JSON / Excel</strong>
              <Input name="file" type="file" accept=".pdf,.json,.xlsx,.xls,.xlsm" required />
              <Button type="submit">Analyze AIS</Button>
            </form>
            <form onSubmit={(e) => upload(e, "26as")} className="grid gap-3 rounded-md border p-4">
              <strong>Form 26AS</strong>
              <Input name="file" type="file" accept=".pdf,.json,.xlsx,.xls,.xlsm" required />
              <Button type="submit">Analyze 26AS</Button>
            </form>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Analysis Result</CardTitle></CardHeader>
          <CardContent>
            <pre className="max-h-[560px] overflow-auto rounded-md bg-muted/10 p-4 text-xs">{result || "Upload a file to see parsed tax intelligence."}</pre>
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
}

