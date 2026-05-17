import React, { useEffect, useRef, useState } from "react";
import { Send, Bot, User, Loader2, Cloud, Zap, Github } from "lucide-react";
import { GitHubPushModal } from "./GitHubPushModal";

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  fileCount?: number;
  timestamp: Date;
}

interface ChatPanelProps {
  messages: Message[];
  loading: boolean;
  onSend: (message: string) => void;
}

export function ChatPanel({ messages, loading, onSend }: ChatPanelProps) {
  const [input, setInput] = useState("");
  const [showGitHub, setShowGitHub] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed || loading) return;
    setInput("");
    onSend(trimmed);
    if (textareaRef.current) textareaRef.current.style.height = "auto";
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    e.target.style.height = "auto";
    e.target.style.height = Math.min(e.target.scrollHeight, 160) + "px";
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        background: "hsl(222 47% 11%)",
        borderRight: "1px solid hsl(222 47% 22%)",
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: "16px 20px",
          borderBottom: "1px solid hsl(222 47% 22%)",
          display: "flex",
          alignItems: "center",
          gap: "10px",
          flexShrink: 0,
        }}
      >
        <div
          style={{
            width: 32,
            height: 32,
            borderRadius: 8,
            background: "linear-gradient(135deg, hsl(262 83% 60%), hsl(220 83% 65%))",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <Zap size={16} color="white" />
        </div>
        <div>
          <div style={{ fontSize: 14, fontWeight: 600, color: "hsl(210 40% 98%)" }}>
            AutoScript-Pro
          </div>
          <div style={{ fontSize: 11, color: "hsl(215 20% 55%)" }}>
            Terraform AI Agent
          </div>
        </div>
        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 10 }}>
          {/* GitHub push button */}
          <button
            onClick={() => setShowGitHub(true)}
            title="Push to GitHub"
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              padding: "5px 12px",
              borderRadius: 7,
              border: "1px solid hsl(222 47% 28%)",
              background: "hsl(222 47% 17%)",
              color: "hsl(215 20% 75%)",
              fontSize: 12,
              fontWeight: 500,
              cursor: "pointer",
              fontFamily: "Inter, sans-serif",
              transition: "all 0.15s",
            }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLButtonElement).style.background = "linear-gradient(135deg, hsl(262 83% 58%), hsl(220 83% 62%))";
              (e.currentTarget as HTMLButtonElement).style.color = "white";
              (e.currentTarget as HTMLButtonElement).style.borderColor = "transparent";
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLButtonElement).style.background = "hsl(222 47% 17%)";
              (e.currentTarget as HTMLButtonElement).style.color = "hsl(215 20% 75%)";
              (e.currentTarget as HTMLButtonElement).style.borderColor = "hsl(222 47% 28%)";
            }}
          >
            <Github size={13} />
            Push
          </button>

          {/* Online indicator */}
          <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: "hsl(142 76% 55%)" }}>
            <div style={{ width: 6, height: 6, borderRadius: "50%", background: "hsl(142 76% 55%)" }} />
            Online
          </div>
        </div>
      </div>

      {/* GitHub push modal */}
      {showGitHub && (
        <GitHubPushModal
          onClose={() => setShowGitHub(false)}
          onSuccess={(msg) => {
            onSend(`[GitHub Push] ${msg}`);
          }}
        />
      )}

      {/* Messages */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "16px",
          display: "flex",
          flexDirection: "column",
          gap: "16px",
        }}
      >
        {messages.length === 0 && (
          <div
            style={{
              flex: 1,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              gap: 12,
              paddingTop: 40,
            }}
          >
            <div
              style={{
                width: 52,
                height: 52,
                borderRadius: 14,
                background: "linear-gradient(135deg, hsl(262 83% 60%), hsl(220 83% 65%))",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <Cloud size={24} color="white" />
            </div>
            <div style={{ textAlign: "center" }}>
              <div
                style={{
                  fontSize: 15,
                  fontWeight: 600,
                  color: "hsl(210 40% 98%)",
                  marginBottom: 6,
                }}
              >
                What do you want to build?
              </div>
              <div style={{ fontSize: 12, color: "hsl(215 20% 55%)", lineHeight: 1.6 }}>
                Describe your infrastructure in plain English.
                <br />
                I'll generate production-ready Terraform code.
              </div>
            </div>
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                gap: 6,
                width: "100%",
                marginTop: 8,
              }}
            >
              {[
                "Generate an S3 bucket with versioning",
                "Create an EC2 instance with security group",
                "Set up a VPC with public and private subnets",
              ].map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => onSend(suggestion)}
                  style={{
                    padding: "8px 12px",
                    background: "hsl(222 47% 17%)",
                    border: "1px solid hsl(222 47% 24%)",
                    borderRadius: 8,
                    color: "hsl(215 20% 75%)",
                    fontSize: 12,
                    cursor: "pointer",
                    textAlign: "left",
                    transition: "all 0.15s",
                  }}
                  onMouseEnter={(e) => {
                    (e.target as HTMLButtonElement).style.background = "hsl(222 47% 20%)";
                    (e.target as HTMLButtonElement).style.color = "hsl(210 40% 95%)";
                  }}
                  onMouseLeave={(e) => {
                    (e.target as HTMLButtonElement).style.background = "hsl(222 47% 17%)";
                    (e.target as HTMLButtonElement).style.color = "hsl(215 20% 75%)";
                  }}
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            style={{
              display: "flex",
              gap: 10,
              alignItems: "flex-start",
              flexDirection: msg.role === "user" ? "row-reverse" : "row",
            }}
          >
            <div
              style={{
                width: 28,
                height: 28,
                borderRadius: "50%",
                flexShrink: 0,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                background:
                  msg.role === "assistant"
                    ? "linear-gradient(135deg, hsl(262 83% 60%), hsl(220 83% 65%))"
                    : "hsl(222 47% 22%)",
              }}
            >
              {msg.role === "assistant" ? (
                <Bot size={14} color="white" />
              ) : (
                <User size={14} color="hsl(215 20% 75%)" />
              )}
            </div>
            <div
              style={{
                maxWidth: "80%",
                display: "flex",
                flexDirection: "column",
                gap: 4,
                alignItems: msg.role === "user" ? "flex-end" : "flex-start",
              }}
            >
              <div
                style={{
                  padding: "10px 14px",
                  borderRadius: msg.role === "user" ? "14px 4px 14px 14px" : "4px 14px 14px 14px",
                  background:
                    msg.role === "user"
                      ? "linear-gradient(135deg, hsl(262 83% 58%), hsl(220 83% 62%))"
                      : "hsl(222 47% 17%)",
                  border:
                    msg.role === "assistant" ? "1px solid hsl(222 47% 24%)" : "none",
                  fontSize: 13,
                  lineHeight: 1.6,
                  color: "hsl(210 40% 96%)",
                  whiteSpace: "pre-wrap",
                  wordBreak: "break-word",
                }}
              >
                {msg.content}
              </div>
              {msg.fileCount && msg.fileCount > 0 && (
                <div
                  style={{
                    fontSize: 11,
                    color: "hsl(142 76% 55%)",
                    display: "flex",
                    alignItems: "center",
                    gap: 4,
                  }}
                >
                  <div
                    style={{
                      width: 5,
                      height: 5,
                      borderRadius: "50%",
                      background: "hsl(142 76% 55%)",
                    }}
                  />
                  {msg.fileCount} file{msg.fileCount > 1 ? "s" : ""} generated
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
            <div
              style={{
                width: 28,
                height: 28,
                borderRadius: "50%",
                flexShrink: 0,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                background:
                  "linear-gradient(135deg, hsl(262 83% 60%), hsl(220 83% 65%))",
              }}
            >
              <Bot size={14} color="white" />
            </div>
            <div
              style={{
                padding: "12px 16px",
                borderRadius: "4px 14px 14px 14px",
                background: "hsl(222 47% 17%)",
                border: "1px solid hsl(222 47% 24%)",
                display: "flex",
                alignItems: "center",
                gap: 8,
              }}
            >
              <Loader2 size={13} color="hsl(262 83% 70%)" className="animate-spin" style={{ animation: "spin 1s linear infinite" }} />
              <span style={{ fontSize: 13, color: "hsl(215 20% 65%)" }}>
                Generating...
              </span>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div
        style={{
          padding: "12px 16px",
          borderTop: "1px solid hsl(222 47% 22%)",
          flexShrink: 0,
        }}
      >
        <div
          style={{
            display: "flex",
            gap: 8,
            alignItems: "flex-end",
            background: "hsl(222 47% 17%)",
            border: "1px solid hsl(222 47% 26%)",
            borderRadius: 12,
            padding: "8px 8px 8px 14px",
            transition: "border-color 0.15s",
          }}
          onFocusCapture={(e) =>
            ((e.currentTarget as HTMLDivElement).style.borderColor =
              "hsl(262 83% 60%)")
          }
          onBlurCapture={(e) =>
            ((e.currentTarget as HTMLDivElement).style.borderColor =
              "hsl(222 47% 26%)")
          }
        >
          <textarea
            ref={textareaRef}
            value={input}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            placeholder="Describe your infrastructure..."
            rows={1}
            style={{
              flex: 1,
              background: "transparent",
              border: "none",
              outline: "none",
              color: "hsl(210 40% 98%)",
              fontSize: 13,
              lineHeight: 1.6,
              resize: "none",
              fontFamily: "Inter, sans-serif",
              paddingTop: 2,
            }}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || loading}
            style={{
              width: 32,
              height: 32,
              borderRadius: 8,
              border: "none",
              cursor: !input.trim() || loading ? "not-allowed" : "pointer",
              background:
                !input.trim() || loading
                  ? "hsl(222 47% 22%)"
                  : "linear-gradient(135deg, hsl(262 83% 58%), hsl(220 83% 62%))",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              transition: "all 0.15s",
              flexShrink: 0,
            }}
          >
            <Send
              size={14}
              color={!input.trim() || loading ? "hsl(215 20% 45%)" : "white"}
            />
          </button>
        </div>
        <div
          style={{
            fontSize: 11,
            color: "hsl(215 20% 45%)",
            marginTop: 6,
            textAlign: "center",
          }}
        >
          Enter to send · Shift+Enter for new line
        </div>
      </div>
    </div>
  );
}
