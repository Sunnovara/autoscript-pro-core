import React, { useState, useCallback } from "react";
import { Panel, PanelGroup, PanelResizeHandle } from "react-resizable-panels";
import { ChatPanel } from "./components/ChatPanel";
import type { Message } from "./components/ChatPanel";
import { CodePanel } from "./components/CodePanel";
import { sendChat } from "./lib/api";

export default function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [files, setFiles] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);

  const handleSend = useCallback(async (text: string) => {
    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content: text,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      const data = await sendChat(text);
      const newFiles = data.files && Object.keys(data.files).length > 0
        ? data.files
        : undefined;

      if (newFiles) setFiles(newFiles);

      const assistantMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: data.response || "Done.",
        fileCount: newFiles ? Object.keys(newFiles).length : 0,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      const errorMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: `Error: ${err.message || "Something went wrong"}`,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  }, []);

  return (
    <div style={{ height: "100vh", width: "100vw", overflow: "hidden" }}>
      <PanelGroup direction="horizontal" style={{ height: "100%" }}>
        {/* Left: Chat */}
        <Panel defaultSize={32} minSize={24} maxSize={45}>
          <ChatPanel
            messages={messages}
            loading={loading}
            onSend={handleSend}
          />
        </Panel>

        {/* Drag handle */}
        <PanelResizeHandle
          style={{
            width: 4,
            background: "hsl(222 47% 22%)",
            cursor: "col-resize",
            transition: "background 0.15s",
            position: "relative",
          }}
          onDragging={(isDragging) => {
            document.body.style.cursor = isDragging ? "col-resize" : "";
          }}
        />

        {/* Right: Code */}
        <Panel defaultSize={68} minSize={40}>
          <CodePanel files={files} />
        </Panel>
      </PanelGroup>
    </div>
  );
}
