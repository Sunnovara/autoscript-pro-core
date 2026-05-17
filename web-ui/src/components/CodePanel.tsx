import React, { useState } from "react";
import Editor from "@monaco-editor/react";
import {
  FileCode,
  Copy,
  Check,
  FileText,
  ChevronRight,
  FolderOpen,
} from "lucide-react";

interface CodePanelProps {
  files: Record<string, string>;
}

const FILE_ICONS: Record<string, React.ReactNode> = {
  "main.tf": <FileCode size={13} color="hsl(262 83% 70%)" />,
  "variables.tf": <FileCode size={13} color="hsl(220 83% 70%)" />,
  "outputs.tf": <FileCode size={13} color="hsl(180 70% 60%)" />,
  "provider.tf": <FileCode size={13} color="hsl(30 90% 60%)" />,
  "terraform.tfvars": <FileText size={13} color="hsl(142 76% 55%)" />,
  "README.md": <FileText size={13} color="hsl(215 20% 65%)" />,
  ".gitignore": <FileText size={13} color="hsl(215 20% 55%)" />,
};

const FILE_ORDER = [
  "main.tf",
  "variables.tf",
  "outputs.tf",
  "provider.tf",
  "terraform.tfvars",
  "README.md",
  ".gitignore",
];

function getLanguage(filename: string): string {
  if (filename.endsWith(".tf") || filename.endsWith(".tfvars")) return "hcl";
  if (filename.endsWith(".md")) return "markdown";
  if (filename.endsWith(".yml") || filename.endsWith(".yaml")) return "yaml";
  if (filename.endsWith(".json")) return "json";
  if (filename.endsWith(".sh")) return "shell";
  return "plaintext";
}

function sortFiles(files: string[]): string[] {
  return [...files].sort((a, b) => {
    const ai = FILE_ORDER.indexOf(a);
    const bi = FILE_ORDER.indexOf(b);
    if (ai === -1 && bi === -1) return a.localeCompare(b);
    if (ai === -1) return 1;
    if (bi === -1) return -1;
    return ai - bi;
  });
}

export function CodePanel({ files }: CodePanelProps) {
  const fileNames = sortFiles(Object.keys(files));
  const [activeFile, setActiveFile] = useState<string | null>(
    fileNames[0] ?? null
  );
  const [copied, setCopied] = useState(false);

  const currentFile = activeFile && files[activeFile] ? activeFile : fileNames[0] ?? null;
  const currentContent = currentFile ? files[currentFile] : "";

  const handleCopy = async () => {
    if (!currentContent) return;
    await navigator.clipboard.writeText(currentContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (fileNames.length === 0) {
    return (
      <div
        style={{
          height: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          background: "hsl(222 47% 12%)",
          gap: 14,
        }}
      >
        <div
          style={{
            width: 56,
            height: 56,
            borderRadius: 14,
            background: "hsl(222 47% 17%)",
            border: "1px solid hsl(222 47% 24%)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <FolderOpen size={24} color="hsl(215 20% 45%)" />
        </div>
        <div style={{ textAlign: "center" }}>
          <div
            style={{
              fontSize: 15,
              fontWeight: 600,
              color: "hsl(210 40% 85%)",
              marginBottom: 6,
            }}
          >
            No files generated yet
          </div>
          <div style={{ fontSize: 12, color: "hsl(215 20% 50%)", lineHeight: 1.6 }}>
            Ask the agent to generate Terraform code.
            <br />
            Files will appear here instantly.
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      style={{
        height: "100%",
        display: "flex",
        flexDirection: "column",
        background: "hsl(222 47% 12%)",
      }}
    >
      {/* Top bar */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0 16px",
          height: 44,
          borderBottom: "1px solid hsl(222 47% 20%)",
          flexShrink: 0,
          gap: 8,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <ChevronRight size={12} color="hsl(215 20% 45%)" />
          <span style={{ fontSize: 12, color: "hsl(215 20% 55%)" }}>
            generated_terraform
          </span>
          <ChevronRight size={12} color="hsl(215 20% 45%)" />
          <span style={{ fontSize: 12, color: "hsl(210 40% 85%)" }}>
            {currentFile}
          </span>
        </div>
        <button
          onClick={handleCopy}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 5,
            padding: "4px 10px",
            background: copied ? "hsl(142 76% 20%)" : "hsl(222 47% 20%)",
            border: `1px solid ${copied ? "hsl(142 76% 35%)" : "hsl(222 47% 28%)"}`,
            borderRadius: 6,
            cursor: "pointer",
            fontSize: 11,
            color: copied ? "hsl(142 76% 65%)" : "hsl(215 20% 70%)",
            transition: "all 0.15s",
          }}
        >
          {copied ? <Check size={12} /> : <Copy size={12} />}
          {copied ? "Copied" : "Copy"}
        </button>
      </div>

      {/* File tabs */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 0,
          overflowX: "auto",
          borderBottom: "1px solid hsl(222 47% 20%)",
          flexShrink: 0,
          background: "hsl(222 47% 11%)",
        }}
      >
        {fileNames.map((name) => {
          const isActive = name === currentFile;
          return (
            <button
              key={name}
              onClick={() => setActiveFile(name)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 6,
                padding: "8px 14px",
                background: isActive ? "hsl(222 47% 15%)" : "transparent",
                border: "none",
                borderBottom: isActive
                  ? "2px solid hsl(262 83% 65%)"
                  : "2px solid transparent",
                cursor: "pointer",
                fontSize: 12,
                color: isActive ? "hsl(210 40% 95%)" : "hsl(215 20% 55%)",
                whiteSpace: "nowrap",
                transition: "all 0.15s",
                fontFamily: "Inter, sans-serif",
              }}
              onMouseEnter={(e) => {
                if (!isActive)
                  (e.currentTarget as HTMLButtonElement).style.color =
                    "hsl(215 20% 75%)";
              }}
              onMouseLeave={(e) => {
                if (!isActive)
                  (e.currentTarget as HTMLButtonElement).style.color =
                    "hsl(215 20% 55%)";
              }}
            >
              {FILE_ICONS[name] ?? <FileCode size={13} color="hsl(215 20% 55%)" />}
              {name}
            </button>
          );
        })}
      </div>

      {/* Editor */}
      <div style={{ flex: 1, overflow: "hidden" }}>
        <Editor
          height="100%"
          language={getLanguage(currentFile ?? "")}
          value={currentContent}
          theme="vs-dark"
          options={{
            readOnly: true,
            minimap: { enabled: false },
            fontSize: 13,
            lineHeight: 22,
            padding: { top: 16, bottom: 16 },
            scrollBeyondLastLine: false,
            wordWrap: "on",
            renderLineHighlight: "all",
            smoothScrolling: true,
            cursorBlinking: "smooth",
            fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace",
            fontLigatures: true,
            lineNumbers: "on",
            folding: true,
            bracketPairColorization: { enabled: true },
          }}
        />
      </div>

      {/* Footer */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "6px 16px",
          borderTop: "1px solid hsl(222 47% 20%)",
          flexShrink: 0,
          background: "hsl(222 47% 10%)",
        }}
      >
        <span style={{ fontSize: 11, color: "hsl(215 20% 45%)" }}>
          {fileNames.length} file{fileNames.length !== 1 ? "s" : ""} ·{" "}
          {getLanguage(currentFile ?? "").toUpperCase()}
        </span>
        <span style={{ fontSize: 11, color: "hsl(215 20% 45%)" }}>
          {currentContent.split("\n").length} lines
        </span>
      </div>
    </div>
  );
}
