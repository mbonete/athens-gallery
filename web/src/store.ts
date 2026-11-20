import { useSyncExternalStore } from "react";
import type { Painting } from "./paintings";

export type Mode = "walk" | "entering" | "detail" | "leaving" | "looking-up" | "dome" | "looking-down";
type State = { mode: Mode; active: Painting | null; ready: boolean; started: boolean };

let state: State = { mode: "walk", active: null, ready: false, started: false };
const listeners = new Set<() => void>();

export const getState = () => state;
export const setState = (patch: Partial<State>) => {
  state = { ...state, ...patch };
  listeners.forEach((l) => l());
};
export const useStore = <T,>(select: (s: State) => T) =>
  useSyncExternalStore(
    (l) => (listeners.add(l), () => listeners.delete(l)),
    () => select(state),
  );
