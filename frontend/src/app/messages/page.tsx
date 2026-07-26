"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileText, Mic, Music, Paperclip, Send, Video } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";

import { RequireUserType } from "@/components/auth/require-user-type";
import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { API_BASE_URL } from "@/lib/api";
import {
  listConversations,
  listMessages,
  markConversationRead,
  sendAttachmentMessage,
  sendTextMessage,
  startConversation,
} from "@/lib/messaging-api";
import type { Conversation, Message, MessageType } from "@/types/messaging";

function resolveUrl(url: string | null): string | undefined {
  if (!url) return undefined;
  return url.startsWith("http") ? url : `${API_BASE_URL}${url}`;
}

function formatTime(iso: string) {
  return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function ConversationRow({ conversation, isActive, onClick }: { conversation: Conversation; isActive: boolean; onClick: () => void }) {
  const preview =
    conversation.last_message?.text_body ??
    (conversation.last_message ? `Sent a ${conversation.last_message.message_type.replace("_", " ")}` : "No messages yet");

  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left transition-colors ${isActive ? "bg-accent" : "hover:bg-muted"}`}
    >
      <Avatar>
        <AvatarImage src={resolveUrl(conversation.counterpart.picture_url)} alt={conversation.counterpart.name} />
        <AvatarFallback>{conversation.counterpart.name.slice(0, 2).toUpperCase()}</AvatarFallback>
      </Avatar>
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-2">
          <span className="truncate text-sm font-medium">{conversation.counterpart.name}</span>
          {conversation.unread_count > 0 && (
            <Badge variant="destructive" className="shrink-0">
              {conversation.unread_count}
            </Badge>
          )}
        </div>
        <p className="truncate text-xs text-muted-foreground">{preview}</p>
      </div>
    </button>
  );
}

function AttachmentBubble({ message }: { message: Message }) {
  const url = resolveUrl(message.attachment_url);
  if (message.message_type === "video") {
    return <video src={url} controls className="max-h-64 rounded-md" />;
  }
  if (message.message_type === "audio" || message.message_type === "voice_note") {
    return (
      <div className="space-y-1">
        <p className="flex items-center gap-1.5 text-xs opacity-80">
          {message.message_type === "voice_note" ? <Mic className="size-3.5" /> : <Music className="size-3.5" />}
          {message.message_type === "voice_note" ? "Voice note" : "Audio"}
        </p>
        <audio src={url} controls className="max-w-full" />
      </div>
    );
  }
  return (
    <a href={url} target="_blank" rel="noreferrer" className="flex items-center gap-2 text-sm underline underline-offset-2">
      <FileText className="size-4" />
      {message.attachment_original_filename ?? "Document"}
    </a>
  );
}

function MessageBubble({ message }: { message: Message }) {
  return (
    <div className={`flex ${message.is_mine ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[75%] space-y-1 rounded-2xl px-3 py-2 text-sm ${message.is_mine ? "bg-primary text-primary-foreground" : "bg-muted text-foreground"}`}
      >
        {message.text_body && message.message_type === "text" && <p className="whitespace-pre-wrap">{message.text_body}</p>}
        {message.message_type !== "text" && <AttachmentBubble message={message} />}
        {message.text_body && message.message_type !== "text" && <p className="whitespace-pre-wrap">{message.text_body}</p>}
        <p className={`text-right text-[10px] ${message.is_mine ? "text-primary-foreground/70" : "text-muted-foreground"}`}>
          {formatTime(message.created_at)}
        </p>
      </div>
    </div>
  );
}

function ChatThread({ conversation }: { conversation: Conversation }) {
  const queryClient = useQueryClient();
  const [text, setText] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const fileInputs = {
    document: useRef<HTMLInputElement>(null),
    audio: useRef<HTMLInputElement>(null),
    voice_note: useRef<HTMLInputElement>(null),
    video: useRef<HTMLInputElement>(null),
  } as const;

  const { data: messages } = useQuery({
    queryKey: ["conversations", conversation.id, "messages"],
    queryFn: () => listMessages(conversation.id),
    refetchInterval: 4000,
  });

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages?.length]);

  useEffect(() => {
    if (conversation.unread_count > 0) {
      markConversationRead(conversation.id).then(() => queryClient.invalidateQueries({ queryKey: ["conversations"] }));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conversation.id]);

  const sendText = useMutation({
    mutationFn: () => sendTextMessage(conversation.id, text),
    onSuccess: () => {
      setText("");
      queryClient.invalidateQueries({ queryKey: ["conversations", conversation.id, "messages"] });
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
    },
  });

  const sendAttachment = useMutation({
    mutationFn: ({ type, file }: { type: MessageType; file: File }) => sendAttachmentMessage(conversation.id, type, file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["conversations", conversation.id, "messages"] });
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
    },
  });

  function handleFileChange(type: MessageType, e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) sendAttachment.mutate({ type, file });
    e.target.value = "";
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between gap-3 border-b px-4 py-3">
        <div className="flex items-center gap-3">
          <Avatar>
            <AvatarImage src={resolveUrl(conversation.counterpart.picture_url)} alt={conversation.counterpart.name} />
            <AvatarFallback>{conversation.counterpart.name.slice(0, 2).toUpperCase()}</AvatarFallback>
          </Avatar>
          <span className="font-medium">{conversation.counterpart.name}</span>
        </div>
        <Button
          size="xs"
          variant="outline"
          render={
            <Link
              href={`/contracts?with=${conversation.counterpart.user_id}&name=${encodeURIComponent(conversation.counterpart.name)}`}
            />
          }
        >
          Propose contract
        </Button>
      </div>

      <div className="flex-1 space-y-2 overflow-y-auto px-4 py-4">
        {messages?.map((m) => <MessageBubble key={m.id} message={m} />)}
        <div ref={bottomRef} />
      </div>

      <div className="space-y-2 border-t p-3">
        <div className="flex items-center gap-1">
          <input ref={fileInputs.document} type="file" accept=".pdf,.doc,.docx,.txt" className="hidden" onChange={(e) => handleFileChange("document", e)} />
          <input ref={fileInputs.audio} type="file" accept="audio/*" className="hidden" onChange={(e) => handleFileChange("audio", e)} />
          <input ref={fileInputs.voice_note} type="file" accept="audio/*" className="hidden" onChange={(e) => handleFileChange("voice_note", e)} />
          <input ref={fileInputs.video} type="file" accept="video/*" className="hidden" onChange={(e) => handleFileChange("video", e)} />
          <Button size="icon-xs" variant="ghost" title="Attach document" onClick={() => fileInputs.document.current?.click()}>
            <Paperclip className="size-4" />
          </Button>
          <Button size="icon-xs" variant="ghost" title="Send audio file" onClick={() => fileInputs.audio.current?.click()}>
            <Music className="size-4" />
          </Button>
          <Button size="icon-xs" variant="ghost" title="Send voice note" onClick={() => fileInputs.voice_note.current?.click()}>
            <Mic className="size-4" />
          </Button>
          <Button size="icon-xs" variant="ghost" title="Send video" onClick={() => fileInputs.video.current?.click()}>
            <Video className="size-4" />
          </Button>
          {sendAttachment.isPending && <span className="text-xs text-muted-foreground">Uploading...</span>}
        </div>
        <form
          className="flex items-center gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            if (text.trim()) sendText.mutate();
          }}
        >
          <Input value={text} onChange={(e) => setText(e.target.value)} placeholder="Type a message..." />
          <Button type="submit" size="icon-sm" disabled={sendText.isPending || !text.trim()}>
            <Send className="size-4" />
          </Button>
        </form>
      </div>
    </div>
  );
}

function MessagesApp() {
  const searchParams = useSearchParams();
  const withParam = searchParams.get("with");
  const queryParam = searchParams.get("q");
  const queryClient = useQueryClient();
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const { data: conversations, isLoading } = useQuery({
    queryKey: ["conversations"],
    queryFn: listConversations,
    refetchInterval: 6000,
  });

  const startMutation = useMutation({
    mutationFn: (counterpartId: string) => startConversation(counterpartId),
    onSuccess: (conversation) => {
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
      setSelectedId(conversation.id);
    },
  });

  const hasRunDeepLink = useRef(false);
  useEffect(() => {
    if (!withParam || hasRunDeepLink.current) return;
    hasRunDeepLink.current = true;
    startMutation.mutate(withParam);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [withParam]);

  const selected = conversations?.find((c) => c.id === selectedId) ?? conversations?.[0] ?? null;

  if (isLoading || startMutation.isPending) return <p className="text-sm text-muted-foreground">Loading conversations...</p>;

  if (startMutation.isError) {
    return (
      <p className="text-sm text-destructive">
        Could not start that conversation — you can only message someone you have an active campaign relationship
        with.
      </p>
    );
  }

  if (!conversations || conversations.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No conversations yet. You can message a brand or influencer once you have an active campaign relationship
        with them (e.g. a claimed slot).
      </p>
    );
  }

  const visibleConversations = queryParam
    ? conversations.filter((c) => c.counterpart.name.toLowerCase().includes(queryParam.toLowerCase()))
    : conversations;

  return (
    <div className="grid h-[70vh] grid-cols-1 overflow-hidden rounded-lg border md:grid-cols-3">
      <div className="space-y-1 overflow-y-auto border-r p-2 md:col-span-1">
        {queryParam && (
          <p className="px-1 pb-1 text-xs text-muted-foreground">
            {visibleConversations.length} result{visibleConversations.length === 1 ? "" : "s"} for &quot;{queryParam}&quot;
          </p>
        )}
        {visibleConversations.length === 0 && <p className="px-1 text-sm text-muted-foreground">No matching conversations.</p>}
        {visibleConversations.map((c) => (
          <ConversationRow key={c.id} conversation={c} isActive={selected?.id === c.id} onClick={() => setSelectedId(c.id)} />
        ))}
      </div>
      <div className="md:col-span-2">{selected && <ChatThread key={selected.id} conversation={selected} />}</div>
    </div>
  );
}

export default function MessagesPage() {
  return (
    <RequireUserType allow={["brand", "influencer"]}>
      <DashboardShell title="Messages">
        <Suspense fallback={<p className="text-sm text-muted-foreground">Loading conversations...</p>}>
          <MessagesApp />
        </Suspense>
      </DashboardShell>
    </RequireUserType>
  );
}
