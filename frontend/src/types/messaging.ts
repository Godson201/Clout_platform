export type MessageType = "text" | "audio" | "video" | "voice_note" | "document";

export interface Counterpart {
  user_id: string;
  name: string;
  picture_url: string | null;
}

export interface Message {
  id: string;
  conversation_id: string;
  sender_user_id: string;
  is_mine: boolean;
  message_type: MessageType;
  text_body: string | null;
  attachment_url: string | null;
  attachment_original_filename: string | null;
  attachment_mime_type: string | null;
  attachment_size_bytes: number | null;
  created_at: string;
  read_at: string | null;
}

export interface Conversation {
  id: string;
  counterpart: Counterpart;
  last_message: Message | null;
  unread_count: number;
  last_message_at: string;
}
