import { api } from "@/lib/api";
import type { Conversation, Message, MessageType } from "@/types/messaging";

export async function listConversations(): Promise<Conversation[]> {
  const { data } = await api.get<Conversation[]>("/conversations");
  return data;
}

export async function startConversation(counterpartId: string): Promise<Conversation> {
  const { data } = await api.post<Conversation>("/conversations", { counterpart_id: counterpartId });
  return data;
}

export async function listMessages(conversationId: string): Promise<Message[]> {
  const { data } = await api.get<Message[]>(`/conversations/${conversationId}/messages`);
  return data;
}

export async function sendTextMessage(conversationId: string, text: string): Promise<Message> {
  const { data } = await api.post<Message>(`/conversations/${conversationId}/messages`, { text });
  return data;
}

export async function sendAttachmentMessage(
  conversationId: string,
  messageType: MessageType,
  file: File,
  caption?: string,
): Promise<Message> {
  const formData = new FormData();
  formData.append("message_type", messageType);
  formData.append("file", file);
  if (caption) formData.append("caption", caption);
  const { data } = await api.post<Message>(`/conversations/${conversationId}/messages/attachment`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function markConversationRead(conversationId: string): Promise<void> {
  await api.post(`/conversations/${conversationId}/read`);
}
