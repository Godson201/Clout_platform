import { api } from "@/lib/api";
import type { Notification } from "@/types/notification";

export async function listNotifications(): Promise<Notification[]> {
  const { data } = await api.get<Notification[]>("/notifications");
  return data;
}

export async function getUnreadNotificationCount(): Promise<number> {
  const { data } = await api.get<{ unread_count: number }>("/notifications/unread-count");
  return data.unread_count;
}

export async function markNotificationRead(id: string): Promise<void> {
  await api.post(`/notifications/${id}/read`);
}

export async function markAllNotificationsRead(): Promise<void> {
  await api.post("/notifications/read-all");
}
