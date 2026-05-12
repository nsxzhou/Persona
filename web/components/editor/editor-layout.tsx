"use client";

import React from "react";

export type EditorLayoutProps = {
  isLeftExpanded: boolean;
  isRightExpanded: boolean;
  quickActions: React.ReactNode;
  leftPanel: React.ReactNode;
  headerLeft: React.ReactNode;
  headerRight: React.ReactNode;
  chapterBanner?: React.ReactNode;
  rightPanel: React.ReactNode;
  rightPanelToggle: React.ReactNode;
  children: React.ReactNode;
};

export function EditorLayout({
  isLeftExpanded,
  isRightExpanded,
  quickActions,
  leftPanel,
  headerLeft,
  headerRight,
  chapterBanner,
  rightPanel,
  rightPanelToggle,
  children,
}: EditorLayoutProps) {
  return (
    <div className="motion-page flex h-screen w-full bg-background text-foreground">
      <div className="motion-nav w-12 shrink-0 bg-[#111] flex flex-col items-center pt-3 gap-1">
        {quickActions}
      </div>

      <div
        className="motion-panel shrink-0 overflow-hidden flex flex-col"
        style={{ width: isLeftExpanded ? 260 : 0 }}
      >
        {leftPanel}
      </div>

      <div className="flex-1 flex flex-col min-w-0">
        <header className="motion-nav border-b shrink-0">
          <div className="flex items-center justify-between px-6 py-3">
            <div className="flex items-center gap-4">
              {headerLeft}
            </div>

            <div className="flex items-center gap-3">
              {headerRight}
            </div>
          </div>

          <div className="px-6 pb-3">
            {chapterBanner}
          </div>
        </header>

        <main className="flex-1 overflow-hidden flex justify-center bg-muted/20">
          {children}
        </main>
      </div>

      {isRightExpanded ? (
        <div
          className="motion-panel shrink-0 overflow-hidden"
          style={{ width: 280 }}
        >
          {rightPanel}
        </div>
      ) : (
        rightPanelToggle
      )}
    </div>
  );
}
