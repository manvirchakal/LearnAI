"use client";
import { Box, TextField, Typography, Paper, Avatar, Alert } from "@mui/material";
import SendIcon from "@mui/icons-material/Send";
import SmartToyIcon from "@mui/icons-material/SmartToy";
import PersonIcon from "@mui/icons-material/Person";
import { useState, useRef, useEffect } from "react";
import Button from "@/components/ui/Button";
import { useStudyStore } from "@/store/studyStore";
import { useSendMessage, useChatHistory } from "@/api/chat";
import type { ChatMessage } from "@/types/chat";

export default function ChatPanel() {
  const { collectionId, sectionName, fileId, userId, language } = useStudyStore();
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  const { data: historyData } = useChatHistory(fileId || "", sectionName || "");
  const { mutate: sendMessage, isPending, error } = useSendMessage();

  const messages: ChatMessage[] = historyData?.history || [];

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = () => {
    if (!input.trim() || !collectionId || !sectionName) return;
    sendMessage({
      message: input.trim(),
      user_id: userId,
      file_id: fileId || "",
      section_name: sectionName,
      collection_id: collectionId,
      language: language || "en",
    });
    setInput("");
  };

  if (!collectionId) {
    return (
      <Box sx={{ p: 4, textAlign: "center" }}>
        <Typography color="text.secondary">Select a section to start chatting.</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ display: "flex", flexDirection: "column", height: "calc(100vh - 180px)", p: 2 }}>
      {/* Messages */}
      <Box sx={{ flex: 1, overflowY: "auto", mb: 2, display: "flex", flexDirection: "column", gap: 1.5 }}>
        {messages.length === 0 && (
          <Box sx={{ textAlign: "center", mt: 4 }}>
            <SmartToyIcon sx={{ fontSize: 40, color: "text.disabled", mb: 1 }} />
            <Typography color="text.secondary" variant="body2">
              Ask anything about this section!
            </Typography>
          </Box>
        )}

        {messages.map((msg, i) => (
          <Box
            key={i}
            sx={{
              display: "flex",
              justifyContent: msg.role === "user" ? "flex-end" : "flex-start",
              gap: 1,
              alignItems: "flex-start",
            }}
          >
            {msg.role === "assistant" && (
              <Avatar sx={{ width: 28, height: 28, bgcolor: "primary.main", mt: 0.5 }}>
                <SmartToyIcon sx={{ fontSize: 16 }} />
              </Avatar>
            )}
            <Paper
              elevation={0}
              sx={{
                maxWidth: "75%",
                p: 1.5,
                borderRadius: 2,
                bgcolor: msg.role === "user" ? "primary.main" : "white",
                color: msg.role === "user" ? "white" : "text.primary",
                border: msg.role === "assistant" ? "1px solid #e9ecef" : "none",
              }}
            >
              <Typography variant="body2" sx={{ whiteSpace: "pre-wrap", lineHeight: 1.6 }}>
                {msg.content}
              </Typography>
            </Paper>
            {msg.role === "user" && (
              <Avatar sx={{ width: 28, height: 28, bgcolor: "secondary.main", mt: 0.5 }}>
                <PersonIcon sx={{ fontSize: 16 }} />
              </Avatar>
            )}
          </Box>
        ))}

        {isPending && (
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <Avatar sx={{ width: 28, height: 28, bgcolor: "primary.main" }}>
              <SmartToyIcon sx={{ fontSize: 16 }} />
            </Avatar>
            <Paper elevation={0} sx={{ p: 1.5, borderRadius: 2, border: "1px solid #e9ecef" }}>
              <Typography variant="body2" color="text.secondary">Thinking…</Typography>
            </Paper>
          </Box>
        )}

        <div ref={bottomRef} />
      </Box>

      {error && <Alert severity="error" sx={{ mb: 1 }}>Failed to send message.</Alert>}

      {/* Input */}
      <Box sx={{ display: "flex", gap: 1 }}>
        <TextField
          fullWidth
          size="small"
          placeholder="Ask a question about this section…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
          multiline
          maxRows={4}
          disabled={isPending}
          sx={{ bgcolor: "white" }}
        />
        <Button
          variant="contained"
          onClick={handleSend}
          disabled={!input.trim() || isPending}
          loading={isPending}
          sx={{ minWidth: 44, px: 1.5 }}
        >
          <SendIcon fontSize="small" />
        </Button>
      </Box>
    </Box>
  );
}
