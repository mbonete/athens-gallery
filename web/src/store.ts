import { useSyncExternalStore } from "react";
import type { Painting } from "./paintings";

export type Mode = "walk" | "entering" | "detail" | "leaving" | "looking-up" | "dome" | "looking-down"
  | "banner-in" | "banner" | "banner-out";
type State = { mode: Mode; active: Painting | null; ready: boolean };

let state: State = { mode: "walk", active: null, ready: false };
const listeners = new Set<() => void>();

export const getState = () => state;
export const setState = (patch: Partial<State>) => {
  state = { ...state, ...patch };
  listeners.forEach((l) => l());
};
/** Call `l` after every change; returns the unsubscribe. */
export const subscribe = (l: () => void) => (listeners.add(l), () => void listeners.delete(l));
export const useStore = <T,>(select: (s: State) => T) => useSyncExternalStore(subscribe, () => select(state));
