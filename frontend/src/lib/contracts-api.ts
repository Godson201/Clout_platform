import { api } from "@/lib/api";
import type { Contract } from "@/types/contract";

export interface ProposeContractInput {
  counterpart_id: string;
  campaign_id?: string;
  title: string;
  terms_text: string;
}

export async function listContracts(): Promise<Contract[]> {
  const { data } = await api.get<Contract[]>("/contracts");
  return data;
}

export async function proposeContract(input: ProposeContractInput): Promise<Contract> {
  const { data } = await api.post<Contract>("/contracts", input);
  return data;
}

export async function getContract(id: string): Promise<Contract> {
  const { data } = await api.get<Contract>(`/contracts/${id}`);
  return data;
}

export async function acceptContract(id: string): Promise<Contract> {
  const { data } = await api.post<Contract>(`/contracts/${id}/accept`);
  return data;
}

export async function declineContract(id: string): Promise<Contract> {
  const { data } = await api.post<Contract>(`/contracts/${id}/decline`);
  return data;
}

export async function cancelContract(id: string): Promise<Contract> {
  const { data } = await api.post<Contract>(`/contracts/${id}/cancel`);
  return data;
}
