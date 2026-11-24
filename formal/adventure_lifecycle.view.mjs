export const title = "Adventure WebSocket Lifecycle, Persistence Retry, and Summary Reveal";

export const colors = {
  init: "blue",
  playing: "teal",
  summary: "purple",
  done: "yellow",
  broken: "pink",
};

export function state(v) {
  if (v.dbRecords > 1) return "Duplicate adventure rows created";
  if (v.clientStaleOverwriteHappened) return "Stale client overwrote conclusion";
  if (v.prematureRevealCrash) return "Reveal crashed before conclusion";
  if (v.summaryEverValid && v.summarySlot === "fallback") return "Valid summary clobbered";
  if (v.unsavedChapterStreamed) return "Chapter streamed without DB record";
  if (v.summaryReadySent) return "Summary ready";
  if (v.initSavePending) {
    return v.initSaveAmbiguousCommit
      ? "Initial save retrying after timeout"
      : "Saving new adventure";
  }
  if (!v.stateInitialized) return "Connected (new session)";
  if (v.adventureId === "none") return "Initialized without adventure ID";
  if (v.serverChapters === 0) return "Adventure created";
  if (v.serverChapters === 1) {
    return v.bgSummaryPending ? "Chapter 1 (summary pending)" : "Chapter 1";
  }
  if (v.serverChapters === 2) return "Conclusion ready";
  return "Summary built, retry save";
}

export function group(v) {
  if (
    v.dbRecords > 1 ||
    v.clientStaleOverwriteHappened ||
    v.prematureRevealCrash ||
    (v.summaryEverValid && v.summarySlot === "fallback") ||
    v.unsavedChapterStreamed
  ) {
    return "broken";
  }
  if (v.summaryReadySent) return "done";
  if (v.serverChapters >= 2) return "summary";
  if (v.serverChapters >= 1) return "playing";
  return "init";
}

export function step(action) {
  switch (action) {
    case "StartInitialSave":
      return "player starts adventure";
    case "InitialSaveAmbiguousTimeout":
      return "initial DB save times out after commit";
    case "InitialSaveSucceeds":
      return "initial DB save returns adventure ID";
    case "InitialSaveExhaustsRetries":
      return "initial DB save exhausts retries";
    case "AdvanceChapter":
      return "next chapter generated";
    case "BackgroundSummarySucceeds":
      return "background chapter summary succeeds";
    case "BackgroundSummaryFails":
      return "background summary task fails";
    case "RevealSummaryWithStaleClientState":
      return "reveal arrives with stale client chapters";
    case "RevealSummaryBeforeConclusion":
      return "reveal arrives before conclusion";
    case "RevealSummarySucceeds":
      return "summary built and saved";
    case "RevealSummarySaveFails":
      return "final summary save fails";
    case "RetryRevealSummarySaveSucceeds":
      return "retry final summary save succeeds";
    case "Done":
      return null;
    default:
      return action;
  }
}
