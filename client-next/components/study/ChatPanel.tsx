"use client";
import { Alert, Avatar, Box, Paper, TextField, Typography } from "@mui/material";
import PersonIcon from "@mui/icons-material/Person";
import SendIcon from "@mui/icons-material/Send";
import SmartToyIcon from "@mui/icons-material/SmartToy";
import { useEffect, useRef, useState } from "react";
import Button from "@/components/ui/Button";
import { errorMessage } from "@/api/client";
import { useChatHistory, useSendMessage } from "@/api/chat";
import { useUIStore } from "@/store/uiStore";
import type { ChatMessage } from "@/types/chat";

interface Props {
  fileId: string;
  sectionId: string;
}

function Bubble({ msg, pending = false }: { msg: ChatMessage; pending?: boolean }) {
  const isUser = msg.role === "user";
  return (
    <Box sx={{ display: "flex", justifyContent: isUser ? "flex-end" : "flex-start", gap: 1, alignItems: "flex-start" }}>
      {!isUser && (
        <Avatar sx={{ width: 28, height: 28, bgcolor: "primary.main", mt: 0.5 }}>
          <SmartToyIcon sx={{ fontSize: 16 }} />
        </Avatar>
      )}
      <Paper
        elevation={0}
        sx={{
          maxWidth: "80%",
          p: 1.5,
          borderRadius: 2,
          opacity: pending ? 0.7 : 1,
          bgcolor: isUser ? "primary.main" : "white",
          color: isUser ? "white" : "text.primary",
          border: isUser ? "none" : "1px solid #e9ecef",
        }}
      >
        <Typography variant="body2" sx={{ whiteSpace: "pre-wrap", lineHeight: 1.6 }}>{msg.content}</Typography>
      </Paper>
      {isUser && (
        <Avatar sx={{ width: 28, height: 28, bgcolor: "secondary.main", mt: 0.5 }}>
          <PersonIcon sx={{ fontSize: 16 }} />
        </Avatar>
      )}
    </Box>
  );
}

export default function ChatPanel({ fileId, sectionId }: Props) {
  const { language } = useUIStore();
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  const { data } = useChatHistory(fileId, sectionId);
  const send = useSendMessage(fileId, sectionId);
  const history = data?.history;

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [history, send.isPending]);

  const handleSend = () => {
    const message = input.trim();
    if (!message || send.isPending) return;
    send.mutate({ message, language }, { onSuccess: () => setInput("") });
  };

  return (
    <Box sx={{ display: "flex", flexDirection: "column", height: "100%", minHeight: 0, p: 2 }}>
      <Box sx={{ flex: 1, overflowY: "auto", mb: 2, display: "flex", flexDirection: "column", gap: 1.5 }}>
        {!history?.length && !send.isPending && (
          <Box sx={{ textAlign: "center", mt: 2 }}>
            <SmartToyIcon sx={{ fontSize: 32, color: "text.disabled", mb: 1 }} />
            <Typography color="text.secondary" variant="body2">Ask anything about this section.</Typography>
          </Box>
        )}
        {history?.map((msg, i) => <Bubble key={i} msg={msg} />)}
        {send.isPending && (
          <>
            <Bubble msg={{ role: "user", content: send.variables.message }} pending />
            <Bubble msg={{ role: "assistant", content: "Thinking…" }} pending />
          </>
        )}
        <div ref={bottomRef} />
      </Box>

      {send.error && <Alert severity="error" sx={{ mb: 1 }}>{errorMessage(send.error)}</Alert>}

      <Box sx={{ display: "flex", gap: 1 }}>
        <TextField
          fullWidth
          size="small"
          placeholder="Ask a question about this section…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSend();
            }
          }}
          multiline
          maxRows={4}
          disabled={send.isPending}
          sx={{ bgcolor: "white" }}
        />
        <Button
          variant="contained"
          onClick={handleSend}
          disabled={!input.trim()}
          loading={send.isPending}
          sx={{ minWidth: 44, px: 1.5 }}
          aria-label="Send"
        >
          <SendIcon fontSize="small" />
        </Button>
      </Box>
    </Box>
  );
}
