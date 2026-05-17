import React, { useState, useEffect, useRef } from "react";
import { Github, X, GitBranch, Key, Loader2, CheckCircle, AlertCircle } from "lucide-react";
import { pushToGitHub } from "../lib/api";

interface GitHubPushModalProps {
  onClose: () => void;
  onSuccess: (message: string) => void;
}

export function GitHubPushModal({ onClose, onSuccess }: GitHubPushModalProps) {
  const [repoUrl, setRepoUrl] = useState("");
  const [token, setToken] = useState("");
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<"idle" | "success" | "error">("idle");
  const [statusMessage, setStatusMessage] = useState("");
  const urlInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    urlInputRef.current?.focus();
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [onClose]);

  const handlePush = async () => {
    if (!repoUrl.trim() || !token.trim()) return;
    setLoading(true);
    setStatus("idle");
    setStatusMessage("");
    try {
      const response = await pushToGitHub(repoUrl.trim(), token.trim());
      setStatus("success");
      setStatusMessage(response);
      setTimeout(() => {
        onSuccess(response);
        onClose();
      }, 1800);
    } catch (err: any) {
      setStatus("error");
      setStatusMessage(err.message || "Push failed. Check your repo URL and token.");
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey && repoUrl.trim() && token.trim()) {
      handlePush();
    }
  };

  const isValid = repoUrl.trim().length > 0 && token.trim().length > 0;

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        style={{
          position: "fixed",
          inset: 0,
          background: "rgba(0,0,0,0.6)",
          backdropFilter: "blur(4px)",
          zIndex: 100,
        }}
      />

      {/* Modal */}
      <div
        style={{
          position: "fixed",
          top: "50%",
          left: "50%",
          transform: "translate(-50%, -50%)",
          zIndex: 101,
          width: 440,
          background: "hsl(222 47% 14%)",
          border: "1px solid hsl(222 47% 26%)",
          borderRadius: 16,
          overflow: "hidden",
          boxShadow: "0 24px 64px rgba(0,0,0,0.5)",
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: "20px 24px 16px",
            borderBottom: "1px solid hsl(222 47% 22%)",
            display: "flex",
            alignItems: "center",
            gap: 12,
          }}
        >
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: 10,
              background: "linear-gradient(135deg, hsl(262 83% 58%), hsl(220 83% 62%))",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flexShrink: 0,
            }}
          >
            <Github size={18} color="white" />
          </div>
          <div>
            <div style={{ fontSize: 15, fontWeight: 600, color: "hsl(210 40% 98%)" }}>
              Push to GitHub
            </div>
            <div style={{ fontSize: 12, color: "hsl(215 20% 55%)", marginTop: 2 }}>
              Commit and push generated Terraform files
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              marginLeft: "auto",
              width: 28,
              height: 28,
              borderRadius: 6,
              border: "none",
              background: "transparent",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "hsl(215 20% 55%)",
            }}
            onMouseEnter={(e) =>
              ((e.currentTarget as HTMLButtonElement).style.background = "hsl(222 47% 22%)")
            }
            onMouseLeave={(e) =>
              ((e.currentTarget as HTMLButtonElement).style.background = "transparent")
            }
          >
            <X size={15} />
          </button>
        </div>

        {/* Body */}
        <div style={{ padding: "20px 24px", display: "flex", flexDirection: "column", gap: 16 }}>

          {/* Repo URL */}
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <label style={{ fontSize: 12, fontWeight: 500, color: "hsl(215 20% 75%)", display: "flex", alignItems: "center", gap: 6 }}>
              <GitBranch size={13} color="hsl(262 83% 70%)" />
              Repository URL
            </label>
            <input
              ref={urlInputRef}
              type="text"
              value={repoUrl}
              onChange={(e) => setRepoUrl(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="https://github.com/your-username/your-repo"
              disabled={loading || status === "success"}
              style={{
                padding: "10px 14px",
                background: "hsl(222 47% 11%)",
                border: "1px solid hsl(222 47% 26%)",
                borderRadius: 8,
                color: "hsl(210 40% 98%)",
                fontSize: 13,
                outline: "none",
                fontFamily: "Inter, sans-serif",
                transition: "border-color 0.15s",
                opacity: loading ? 0.6 : 1,
              }}
              onFocus={(e) => (e.target.style.borderColor = "hsl(262 83% 60%)")}
              onBlur={(e) => (e.target.style.borderColor = "hsl(222 47% 26%)")}
            />
          </div>

          {/* PAT */}
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <label style={{ fontSize: 12, fontWeight: 500, color: "hsl(215 20% 75%)", display: "flex", alignItems: "center", gap: 6 }}>
              <Key size={13} color="hsl(262 83% 70%)" />
              Personal Access Token
            </label>
            <input
              type="password"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="ghp_xxxxxxxxxxxxxxxxxxxx"
              disabled={loading || status === "success"}
              style={{
                padding: "10px 14px",
                background: "hsl(222 47% 11%)",
                border: "1px solid hsl(222 47% 26%)",
                borderRadius: 8,
                color: "hsl(210 40% 98%)",
                fontSize: 13,
                outline: "none",
                fontFamily: "monospace",
                transition: "border-color 0.15s",
                opacity: loading ? 0.6 : 1,
                letterSpacing: "0.05em",
              }}
              onFocus={(e) => (e.target.style.borderColor = "hsl(262 83% 60%)")}
              onBlur={(e) => (e.target.style.borderColor = "hsl(222 47% 26%)")}
            />
            <div style={{ fontSize: 11, color: "hsl(215 20% 45%)" }}>
              Needs repo scope. Token is never stored.
            </div>
          </div>

          {/* Status message */}
          {status !== "idle" && (
            <div
              style={{
                padding: "10px 14px",
                borderRadius: 8,
                display: "flex",
                alignItems: "flex-start",
                gap: 8,
                background:
                  status === "success" ? "hsl(142 76% 10%)" : "hsl(0 84% 10%)",
                border: `1px solid ${status === "success" ? "hsl(142 76% 25%)" : "hsl(0 84% 30%)"}`,
              }}
            >
              {status === "success" ? (
                <CheckCircle size={15} color="hsl(142 76% 55%)" style={{ flexShrink: 0, marginTop: 1 }} />
              ) : (
                <AlertCircle size={15} color="hsl(0 84% 60%)" style={{ flexShrink: 0, marginTop: 1 }} />
              )}
              <span
                style={{
                  fontSize: 12,
                  color: status === "success" ? "hsl(142 76% 65%)" : "hsl(0 84% 70%)",
                  lineHeight: 1.5,
                }}
              >
                {statusMessage}
              </span>
            </div>
          )}
        </div>

        {/* Footer */}
        <div
          style={{
            padding: "16px 24px",
            borderTop: "1px solid hsl(222 47% 22%)",
            display: "flex",
            gap: 10,
            justifyContent: "flex-end",
          }}
        >
          <button
            onClick={onClose}
            disabled={loading}
            style={{
              padding: "8px 16px",
              borderRadius: 8,
              border: "1px solid hsl(222 47% 28%)",
              background: "transparent",
              color: "hsl(215 20% 65%)",
              fontSize: 13,
              cursor: loading ? "not-allowed" : "pointer",
              fontFamily: "Inter, sans-serif",
              transition: "all 0.15s",
            }}
            onMouseEnter={(e) => {
              if (!loading)
                (e.currentTarget as HTMLButtonElement).style.background = "hsl(222 47% 20%)";
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLButtonElement).style.background = "transparent";
            }}
          >
            Cancel
          </button>
          <button
            onClick={handlePush}
            disabled={!isValid || loading || status === "success"}
            style={{
              padding: "8px 20px",
              borderRadius: 8,
              border: "none",
              background:
                !isValid || loading || status === "success"
                  ? "hsl(222 47% 22%)"
                  : "linear-gradient(135deg, hsl(262 83% 58%), hsl(220 83% 62%))",
              color:
                !isValid || loading || status === "success"
                  ? "hsl(215 20% 45%)"
                  : "white",
              fontSize: 13,
              fontWeight: 500,
              cursor: !isValid || loading || status === "success" ? "not-allowed" : "pointer",
              fontFamily: "Inter, sans-serif",
              display: "flex",
              alignItems: "center",
              gap: 7,
              transition: "all 0.15s",
            }}
          >
            {loading ? (
              <>
                <Loader2 size={13} style={{ animation: "spin 1s linear infinite" }} />
                Pushing...
              </>
            ) : status === "success" ? (
              <>
                <CheckCircle size={13} />
                Pushed!
              </>
            ) : (
              <>
                <Github size={13} />
                Push to GitHub
              </>
            )}
          </button>
        </div>
      </div>
    </>
  );
}
