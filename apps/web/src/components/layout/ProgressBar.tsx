"use client";

import { AppProgressBar } from "next-nprogress-bar";

export function ProgressBarProvider() {
  return (
    <AppProgressBar
      height="3px"
      color="#2563eb"
      options={{ showSpinner: false }}
      shallowRouting
    />
  );
}
