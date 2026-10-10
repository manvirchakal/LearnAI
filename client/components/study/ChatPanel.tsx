"use client";
import { useChat } from "@ai-sdk/react";
import { useQueryClient } from "@tanstack/react-query";
import { DefaultChatTransport, type UIMessage } from "ai";
import { CheckIcon, CopyIcon, GraduationCapIcon, RotateCcwIcon } from "lucide-react";
import { useMemo, useState } from "react";
import {
  Conversation,
  ConversationContent,
  ConversationEmptyState,
  ConversationScrollButton,
} from "@/components/ai-elements/conversation";
import { Message, MessageAction, MessageActions, MessageContent, MessageResponse } from "@/components/ai-elements/message";
import {
  PromptInput,
  PromptInputBody,
  PromptInputFooter,
  PromptInputSubmit,
  PromptInputTextarea,
  PromptInputTools,
} from "@/components/ai-elements/prompt-input";
import { Shimmer } from "@/components/ai-elements/shimmer";
import { Suggestion, Suggestions } from "@/components/ai-elements/suggestion";
import { ErrorAlert, LoadingState } from "@/components/shared/States";
import { Button } from "@/components/ui/button";
import { API_BASE, USER_ID, errorMessage } from "@/api/client";
import { chatKey, useChatHistory } from "@/api/chat";
import type { StudyUnit } from "@/api/study";
import { useUIStore } from "@/store/uiStore";
import type { ChatMessage } from "@/types/chat";

interface Props {
  unit: StudyUnit;
  /** What the learner is chatting about, e.g. "this section" */
  subject?: string;
}

const SUGGESTIONS = [
  "Summarize the key ideas",
  "Explain it like I'm new to this",
  "Quiz me with three questions",
  "Give me a real-world example",
];

/** Label for the work after a chat-graph node finishes (data-stage parts from the server). */
const NEXT_ACTIVITY: Record<string, string> = {
  load_context: "Reading the material…",
  translate_input: "Thinking…",
  search_materials: "Searching your materials…",
  read_materials: "Reading your materials…",
  tools: "Thinking…",
  tutor: "Translating…",
};

const textOf = (m: UIMessage) =>
  m.parts.map((p) => (p.type === "text" ? p.text : "")).join("");

const toUIMessages = (history: ChatMessage[]): UIMessage[] =>
  history.map((m, i) => ({ id: `history-${i}`, role: m.role, parts: [{ type: "text", text: m.content }] }));

function CopyAction({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <MessageAction
      tooltip={copied ? "Copied" : "Copy"}
      onClick={() => {
        void navigator.clipboard.writeText(text).then(() => {
          setCopied(true);
          setTimeout(() => setCopied(false), 1500);
        });
      }}
    >
      {copied ? <CheckIcon /> : <CopyIcon />}
    </MessageAction>
  );
}

function ChatConversation({ unit, subject, initial }: Required<Props> & { initial: UIMessage[] }) {
  const qc = useQueryClient();
  const { language } = useUIStore();
  const [activity, setActivity] = useState<string | null>(null);

  // The server keeps the history; each request carries just the new message.
  const transport = useMemo(
    () =>
      new DefaultChatTransport<UIMessage>({
        api: `${API_BASE}${unit}/chat/stream`,
        headers: { "X-User-Id": USER_ID },
        prepareSendMessagesRequest: ({ messages, body }) => {
          const lastUser = messages.findLast((m) => m.role === "user");
          return { body: { message: lastUser ? textOf(lastUser) : "", language: body?.language ?? "en" } };
        },
      }),
    [unit],
  );

  const { messages, sendMessage, regenerate, status, stop, error, clearError } = useChat({
    id: unit,
    messages: initial,
    transport,
    onData: (part) => {
      if (part.type === "data-stage") setActivity(NEXT_ACTIVITY[part.data as string] ?? null);
    },
    onFinish: () => {
      setActivity(null);
      void qc.invalidateQueries({ queryKey: chatKey(unit) });
    },
    onError: () => setActivity(null),
  });

  const send = (text: string) => {
    if (!text.trim() || status === "submitted" || status === "streaming") return;
    clearError();
    void sendMessage({ text: text.trim() }, { body: { language } });
  };

  const last = messages.at(-1);
  const waiting = status === "submitted" || (status === "streaming" && last?.role === "assistant" && !textOf(last));

  return (
    <div className="flex h-full min-h-0 flex-col">
      <Conversation className="min-h-0">
        <ConversationContent className="gap-6 px-4 py-5">
          {messages.length === 0 ? (
            <ConversationEmptyState className="py-10">
              <span className="flex size-12 items-center justify-center rounded-2xl bg-primary/10 text-primary ring-1 ring-primary/15">
                <GraduationCapIcon className="size-6" />
              </span>
              <div className="space-y-1">
                <h3 className="font-medium">Your study buddy</h3>
                <p className="text-sm text-muted-foreground">Ask anything about {subject}.</p>
              </div>
            </ConversationEmptyState>
          ) : (
            messages.map((m) => {
              const text = textOf(m);
              if (m.role === "assistant" && !text) return null;
              const isLast = m.id === last?.id;
              return (
                <Message key={m.id} from={m.role}>
                  <MessageContent>
                    {m.role === "assistant" ? (
                      <MessageResponse isAnimating={isLast && status === "streaming"}>{text}</MessageResponse>
                    ) : (
                      <p className="whitespace-pre-wrap">{text}</p>
                    )}
                  </MessageContent>
                  {m.role === "assistant" && !(isLast && status === "streaming") && (
                    <MessageActions className="opacity-0 transition-opacity group-hover:opacity-100 pointer-coarse:opacity-100">
                      <CopyAction text={text} />
                    </MessageActions>
                  )}
                </Message>
              );
            })
          )}
          {waiting && (
            <Message from="assistant">
              <MessageContent>
                <Shimmer className="text-sm">{activity ?? "Thinking…"}</Shimmer>
              </MessageContent>
            </Message>
          )}
          {error && (
            <ErrorAlert
              action={
                <Button size="sm" variant="outline" onClick={() => void regenerate({ body: { language } })}>
                  <RotateCcwIcon />
                  Retry
                </Button>
              }
            >
              {errorMessage(error)}
            </ErrorAlert>
          )}
        </ConversationContent>
        <ConversationScrollButton />
      </Conversation>

      <div className="space-y-3 border-t bg-background/60 p-3">
        {messages.length === 0 && (
          <Suggestions>
            {SUGGESTIONS.map((s) => (
              <Suggestion key={s} suggestion={s} onClick={send} className="text-xs" />
            ))}
          </Suggestions>
        )}
        <PromptInput onSubmit={({ text }) => send(text)}>
          <PromptInputBody>
            <PromptInputTextarea placeholder={`Ask about ${subject}…`} className="min-h-12" />
          </PromptInputBody>
          <PromptInputFooter>
            <PromptInputTools>
              <span className="px-2 text-xs text-muted-foreground pointer-coarse:hidden">Enter to send · Shift+Enter for a new line</span>
            </PromptInputTools>
            <PromptInputSubmit status={status} onStop={stop} />
          </PromptInputFooter>
        </PromptInput>
      </div>
    </div>
  );
}

/** Tutoring chat for a study unit, streamed with the AI SDK's useChat. */
export default function ChatPanel({ unit, subject = "this section" }: Props) {
  const history = useChatHistory(unit);

  if (history.isPending) return <LoadingState label="Loading conversation…" />;
  if (history.error) {
    return (
      <div className="p-4">
        <ErrorAlert title="Couldn't load the conversation">{errorMessage(history.error)}</ErrorAlert>
      </div>
    );
  }
  // Seeds useChat with the stored history; it keeps its own state from then on
  return <ChatConversation key={unit} unit={unit} subject={subject} initial={toUIMessages(history.data.history)} />;
}
