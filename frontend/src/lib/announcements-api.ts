import { api } from "@/lib/api";
import type { Announcement, AnnouncementAudience } from "@/types/announcement";

export async function listAnnouncements(): Promise<Announcement[]> {
  const { data } = await api.get<Announcement[]>("/announcements");
  return data;
}

export async function listAllAnnouncementsAdmin(): Promise<Announcement[]> {
  const { data } = await api.get<Announcement[]>("/admin/announcements");
  return data;
}

export async function createAnnouncement(input: {
  title: string;
  body: string;
  audience: AnnouncementAudience;
}): Promise<Announcement> {
  const { data } = await api.post<Announcement>("/admin/announcements", input);
  return data;
}

export async function setAnnouncementActive(id: string, isActive: boolean): Promise<Announcement> {
  const { data } = await api.patch<Announcement>(`/admin/announcements/${id}`, { is_active: isActive });
  return data;
}
