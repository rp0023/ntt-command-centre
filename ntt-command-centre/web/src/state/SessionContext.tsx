import { createContext, useContext } from "react";
import type { SessionUser } from "../api/client";

export const SessionContext = createContext<SessionUser | null>(null);
export function useSession(): SessionUser {
  const user = useContext(SessionContext);
  if (!user) throw new Error("Sign in before mounting the application");
  return user;
}
