import { hostHeaders, memberHeaders, request } from './client'
import type {
  BillPatch,
  CreatedSession,
  ItemInput,
  ItemPatch,
  JoinResult,
  Session,
} from './types'

const splitPath = (sessionId: string) => `/sessions/${encodeURIComponent(sessionId)}`

// Host calls send the host token. Guest calls send the member token. Both return the whole split.

export function createSession(file: File, note: string): Promise<CreatedSession> {
  const form = new FormData()
  form.append('file', file)
  if (note.trim()) {
    form.append('note', note.trim())
  }
  return request<CreatedSession>('/sessions', { method: 'POST', form })
}

export function updateBill(sessionId: string, hostToken: string, patch: BillPatch): Promise<Session> {
  return request<Session>(splitPath(sessionId), {
    method: 'PATCH',
    body: patch,
    headers: hostHeaders(hostToken),
  })
}

export function addItem(sessionId: string, hostToken: string, input: ItemInput): Promise<Session> {
  return request<Session>(`${splitPath(sessionId)}/items`, {
    method: 'POST',
    body: input,
    headers: hostHeaders(hostToken),
  })
}

export function updateItem(
  sessionId: string,
  hostToken: string,
  itemId: number,
  patch: ItemPatch,
): Promise<Session> {
  return request<Session>(`${splitPath(sessionId)}/items/${itemId}`, {
    method: 'PATCH',
    body: patch,
    headers: hostHeaders(hostToken),
  })
}

export function deleteItem(sessionId: string, hostToken: string, itemId: number): Promise<Session> {
  return request<Session>(`${splitPath(sessionId)}/items/${itemId}`, {
    method: 'DELETE',
    headers: hostHeaders(hostToken),
  })
}

export function addMember(sessionId: string, hostToken: string, name: string): Promise<Session> {
  return request<Session>(`${splitPath(sessionId)}/members`, {
    method: 'POST',
    body: { name },
    headers: hostHeaders(hostToken),
  })
}

export function removeMember(sessionId: string, hostToken: string, memberId: number): Promise<Session> {
  return request<Session>(`${splitPath(sessionId)}/members/${memberId}`, {
    method: 'DELETE',
    headers: hostHeaders(hostToken),
  })
}

export function releaseMember(sessionId: string, hostToken: string, memberId: number): Promise<Session> {
  return request<Session>(`${splitPath(sessionId)}/members/${memberId}/release`, {
    method: 'POST',
    headers: hostHeaders(hostToken),
  })
}

export function unlockMember(sessionId: string, hostToken: string, memberId: number): Promise<Session> {
  return request<Session>(`${splitPath(sessionId)}/members/${memberId}/unlock`, {
    method: 'POST',
    headers: hostHeaders(hostToken),
  })
}

export function markReady(sessionId: string, hostToken: string): Promise<Session> {
  return request<Session>(`${splitPath(sessionId)}/ready`, {
    method: 'POST',
    headers: hostHeaders(hostToken),
  })
}

export function joinSession(sessionId: string, name: string): Promise<JoinResult> {
  return request<JoinResult>(`${splitPath(sessionId)}/join`, {
    method: 'POST',
    body: { name },
  })
}

export function claimItem(
  sessionId: string,
  memberToken: string,
  itemId: number,
  quantity: number,
): Promise<Session> {
  return request<Session>(`${splitPath(sessionId)}/items/${itemId}/claim`, {
    method: 'PUT',
    body: { quantity },
    headers: memberHeaders(memberToken),
  })
}

export function confirmClaims(sessionId: string, memberToken: string): Promise<Session> {
  return request<Session>(`${splitPath(sessionId)}/confirm`, {
    method: 'POST',
    headers: memberHeaders(memberToken),
  })
}
