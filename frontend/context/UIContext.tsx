"use client";

import { createContext, useContext, useState, type ReactNode } from "react";

interface UIContextValue {
  portfolioMode: boolean;
  setPortfolioMode: (value: boolean) => void;
  togglePortfolioMode: () => void;
}

const UIContext = createContext<UIContextValue | null>(null);

export function UIProvider({ children }: { children: ReactNode }) {
  const [portfolioMode, setPortfolioMode] = useState(false);

  return (
    <UIContext.Provider
      value={{
        portfolioMode,
        setPortfolioMode,
        togglePortfolioMode: () => setPortfolioMode((v) => !v),
      }}
    >
      {children}
    </UIContext.Provider>
  );
}

export function useUI() {
  const ctx = useContext(UIContext);
  if (!ctx) throw new Error("useUI must be used within UIProvider");
  return ctx;
}
