"use client";

import { useParams } from "next/navigation";
import type { ReactNode } from "react";

const links = ["", "evidence", "coverage", "processing", "timeline", "comparison", "findings", "report"];

export default function CaseLayout({ children }: { children: ReactNode }) {
  const params = useParams<{ caseId: string }>();
  return (
    <div className="grid gap-6 md:grid-cols-[180px_1fr]">
      <nav className="space-y-2 text-sm">
        {links.map((link) => (
          <a key={link || "overview"} className="block rounded px-2 py-1 hover:bg-white" href={`/cases/${params.caseId}${link ? `/${link}` : ""}`}>
            {link || "overview"}
          </a>
        ))}
      </nav>
      <div>{children}</div>
    </div>
  );
}
