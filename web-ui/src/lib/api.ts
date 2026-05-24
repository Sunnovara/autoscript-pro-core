export type CloudProvider = "aws" | "azure";

export interface ChatResponse {
  response: string;
  files?: Record<string, string>;
  error?: string;
}

export async function sendChat(message: string): Promise<ChatResponse> {
  const res = await fetch("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Request failed: ${res.status}`);
  }
  return res.json();
}

export async function getFiles(): Promise<Record<string, string>> {
  const res = await fetch("/get-files");
  if (!res.ok) throw new Error("Failed to fetch files");
  const data = await res.json();
  return data.files || {};
}

export async function pushToGitHub(repoUrl: string, githubToken: string): Promise<string> {
  const res = await fetch("/push", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ repo_url: repoUrl, github_token: githubToken }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Push failed: ${res.status}`);
  }
  const data = await res.json();
  return data.agent_response || "Pushed successfully.";
}
