---- MODULE AdventureLifecycle ----
EXTENDS Naturals

CONSTANTS
    StoryLength,
    BugStaleClientOverwrite,
    BugPrematureReveal,
    BugUnlockedSummaryFallback,
    BugNonIdempotentInitialRetry,
    BugRetainStateOnInitialSaveFailure

VARIABLES
    stateInitialized,
    adventureId,
    serverChapters,
    dbRecords,
    dbChapters,
    dbComplete,
    summarySlot,
    summaryEverValid,
    bgSummaryPending,
    summaryReadySent,
    unsavedChapterStreamed,
    clientStaleOverwriteHappened,
    prematureRevealCrash,
    initSavePending,
    initSaveAmbiguousCommit

vars == <<
    stateInitialized,
    adventureId,
    serverChapters,
    dbRecords,
    dbChapters,
    dbComplete,
    summarySlot,
    summaryEverValid,
    bgSummaryPending,
    summaryReadySent,
    unsavedChapterStreamed,
    clientStaleOverwriteHappened,
    prematureRevealCrash,
    initSavePending,
    initSaveAmbiguousCommit
>>

TypeOK ==
    /\ stateInitialized \in BOOLEAN
    /\ adventureId \in {"none", "assigned"}
    /\ serverChapters \in 0..(StoryLength + 1)
    /\ dbRecords \in 0..2
    /\ dbChapters \in 0..(StoryLength + 1)
    /\ dbComplete \in BOOLEAN
    /\ summarySlot \in {"empty", "fallback", "valid"}
    /\ summaryEverValid \in BOOLEAN
    /\ bgSummaryPending \in BOOLEAN
    /\ summaryReadySent \in BOOLEAN
    /\ unsavedChapterStreamed \in BOOLEAN
    /\ clientStaleOverwriteHappened \in BOOLEAN
    /\ prematureRevealCrash \in BOOLEAN
    /\ initSavePending \in BOOLEAN
    /\ initSaveAmbiguousCommit \in BOOLEAN

Init ==
    /\ stateInitialized = FALSE
    /\ adventureId = "none"
    /\ serverChapters = 0
    /\ dbRecords = 0
    /\ dbChapters = 0
    /\ dbComplete = FALSE
    /\ summarySlot = "empty"
    /\ summaryEverValid = FALSE
    /\ bgSummaryPending = FALSE
    /\ summaryReadySent = FALSE
    /\ unsavedChapterStreamed = FALSE
    /\ clientStaleOverwriteHappened = FALSE
    /\ prematureRevealCrash = FALSE
    /\ initSavePending = FALSE
    /\ initSaveAmbiguousCommit = FALSE

(*
 * websocket_router.py:609-648
 * First client message initializes AdventureState and starts bounded initial save.
 *)
StartInitialSave ==
    /\ ~stateInitialized
    /\ ~initSavePending
    /\ stateInitialized' = TRUE
    /\ initSavePending' = TRUE
    /\ UNCHANGED <<
        adventureId, serverChapters, dbRecords, dbChapters, dbComplete,
        summarySlot, summaryEverValid, bgSummaryPending, summaryReadySent,
        unsavedChapterStreamed, clientStaleOverwriteHappened,
        prematureRevealCrash, initSaveAmbiguousCommit
        >>

(*
 * persistence.py:36-47
 * Attempt 1 commits row in Supabase, but response times out before returning ID.
 *)
InitialSaveAmbiguousTimeout ==
    /\ initSavePending
    /\ ~initSaveAmbiguousCommit
    /\ dbRecords = 0
    /\ dbRecords' = 1
    /\ initSaveAmbiguousCommit' = TRUE
    /\ UNCHANGED <<
        stateInitialized, adventureId, serverChapters, dbChapters, dbComplete,
        summarySlot, summaryEverValid, bgSummaryPending, summaryReadySent,
        unsavedChapterStreamed, clientStaleOverwriteHappened,
        prematureRevealCrash, initSavePending
        >>

(*
 * persistence.py:36-47
 * Initial save succeeds (either cleanly or on retry after ambiguous timeout).
 * Preallocated new_adventure_id upserts the same row; without it, retry inserts a duplicate.
 *)
InitialSaveSucceeds ==
    /\ initSavePending
    /\ adventureId' = "assigned"
    /\ initSavePending' = FALSE
    /\ initSaveAmbiguousCommit' = FALSE
    /\ dbRecords' =
        IF initSaveAmbiguousCommit THEN
            (IF BugNonIdempotentInitialRetry THEN dbRecords + 1 ELSE dbRecords)
        ELSE
            1
    /\ UNCHANGED <<
        stateInitialized, serverChapters, dbChapters, dbComplete,
        summarySlot, summaryEverValid, bgSummaryPending, summaryReadySent,
        unsavedChapterStreamed, clientStaleOverwriteHappened,
        prematureRevealCrash
        >>

(*
 * websocket_router.py:649-650
 * Initial save exhausts all retries and sends save_failed.
 * Live bug (BugRetainStateOnInitialSaveFailure): stateInitialized stayed TRUE
 * while adventureId stayed "none".
 *)
InitialSaveExhaustsRetries ==
    /\ initSavePending
    /\ initSavePending' = FALSE
    /\ initSaveAmbiguousCommit' = FALSE
    /\ stateInitialized' = BugRetainStateOnInitialSaveFailure
    /\ UNCHANGED <<
        adventureId, serverChapters, dbRecords, dbChapters, dbComplete,
        summarySlot, summaryEverValid, bgSummaryPending, summaryReadySent,
        unsavedChapterStreamed, clientStaleOverwriteHappened,
        prematureRevealCrash
        >>

(*
 * websocket_router.py:775-865
 * Advance one chapter (Ch1..StoryLength). If adventureId = "none", persistence is skipped.
 *)
AdvanceChapter ==
    /\ stateInitialized
    /\ ~initSavePending
    /\ serverChapters < StoryLength
    /\ serverChapters' = serverChapters + 1
    /\ dbChapters' =
        IF adventureId = "assigned" THEN serverChapters + 1 ELSE dbChapters
    /\ unsavedChapterStreamed' =
        (unsavedChapterStreamed \/ (adventureId = "none"))
    /\ bgSummaryPending' =
        IF serverChapters = 1 THEN TRUE ELSE bgSummaryPending
    /\ UNCHANGED <<
        stateInitialized, adventureId, dbRecords, dbComplete,
        summarySlot, summaryEverValid, summaryReadySent,
        clientStaleOverwriteHappened, prematureRevealCrash,
        initSavePending, initSaveAmbiguousCommit
        >>

(*
 * choice_processor.py:1484-1607 (_store_summary_safe / generate_chapter_summary_background)
 * Background chapter summary succeeds and stores a valid summary under summary_lock.
 *)
BackgroundSummarySucceeds ==
    /\ bgSummaryPending
    /\ summarySlot' = "valid"
    /\ summaryEverValid' = TRUE
    /\ bgSummaryPending' = FALSE
    /\ UNCHANGED <<
        stateInitialized, adventureId, serverChapters, dbRecords, dbChapters,
        dbComplete, summaryReadySent, unsavedChapterStreamed,
        clientStaleOverwriteHappened, prematureRevealCrash,
        initSavePending, initSaveAmbiguousCommit
        >>

(*
 * choice_processor.py:1516, 1599-1606
 * A failing duplicate/background summary task writes fallback only when no valid
 * summary exists (overwrite_existing=False). Replays bf68786 when bug flag is TRUE.
 *)
BackgroundSummaryFails ==
    /\ serverChapters >= 1
    /\ ~summaryReadySent
    /\ summarySlot' =
        IF BugUnlockedSummaryFallback THEN "fallback"
        ELSE IF summarySlot = "valid" THEN "valid"
        ELSE "fallback"
    /\ bgSummaryPending' = FALSE
    /\ UNCHANGED <<
        stateInitialized, adventureId, serverChapters, dbRecords, dbChapters,
        dbComplete, summaryEverValid, summaryReadySent, unsavedChapterStreamed,
        clientStaleOverwriteHappened, prematureRevealCrash,
        initSavePending, initSaveAmbiguousCommit
        >>

(*
 * websocket_router.py:696-740 (replays 3dfb9bd)
 * Client sends reveal_summary carrying stale client state (fewer chapters than server).
 *)
RevealSummaryWithStaleClientState ==
    /\ stateInitialized
    /\ ~initSavePending
    /\ serverChapters = StoryLength
    /\ ~summaryReadySent
    /\ IF BugStaleClientOverwrite THEN
           /\ serverChapters' = serverChapters - 1
           /\ clientStaleOverwriteHappened' = TRUE
       ELSE
           /\ UNCHANGED <<serverChapters, clientStaleOverwriteHappened>>
    /\ UNCHANGED <<
        stateInitialized, adventureId, dbRecords, dbChapters, dbComplete,
        summarySlot, summaryEverValid, bgSummaryPending, summaryReadySent,
        unsavedChapterStreamed, prematureRevealCrash,
        initSavePending, initSaveAmbiguousCommit
        >>

(*
 * choice_processor.py:237-255 (replays f4b9b11)
 * Client sends reveal_summary before CONCLUSION chapter exists.
 *)
RevealSummaryBeforeConclusion ==
    /\ stateInitialized
    /\ ~initSavePending
    /\ serverChapters < StoryLength
    /\ ~summaryReadySent
    /\ prematureRevealCrash' = (prematureRevealCrash \/ BugPrematureReveal)
    /\ UNCHANGED <<
        stateInitialized, adventureId, serverChapters, dbRecords, dbChapters,
        dbComplete, summarySlot, summaryEverValid, bgSummaryPending,
        summaryReadySent, unsavedChapterStreamed, clientStaleOverwriteHappened,
        initSavePending, initSaveAmbiguousCommit
        >>

(*
 * choice_processor.py:124-236
 * Valid reveal_summary at CONCLUSION: awaits pending tasks, appends SUMMARY chapter,
 * persists is_complete=TRUE, and sends summary_ready.
 *)
RevealSummarySucceeds ==
    /\ stateInitialized
    /\ ~initSavePending
    /\ adventureId = "assigned"
    /\ serverChapters = StoryLength
    /\ ~summaryReadySent
    /\ bgSummaryPending' = FALSE
    /\ serverChapters' = StoryLength + 1
    /\ dbChapters' = StoryLength + 1
    /\ dbComplete' = TRUE
    /\ summaryReadySent' = TRUE
    /\ summarySlot' = IF summarySlot = "empty" THEN "valid" ELSE summarySlot
    /\ summaryEverValid' = (summaryEverValid \/ (summarySlot = "empty"))
    /\ UNCHANGED <<
        stateInitialized, adventureId, dbRecords,
        unsavedChapterStreamed, clientStaleOverwriteHappened,
        prematureRevealCrash, initSavePending, initSaveAmbiguousCommit
        >>

(*
 * choice_processor.py:210-227
 * reveal_summary appends SUMMARY chapter in memory, then final save exhausts retries.
 * Does NOT send summary_ready; keeps SUMMARY chapter in memory for idempotent retry.
 *)
RevealSummarySaveFails ==
    /\ stateInitialized
    /\ ~initSavePending
    /\ adventureId = "assigned"
    /\ serverChapters = StoryLength
    /\ ~summaryReadySent
    /\ bgSummaryPending' = FALSE
    /\ serverChapters' = StoryLength + 1
    /\ summarySlot' = IF summarySlot = "empty" THEN "valid" ELSE summarySlot
    /\ summaryEverValid' = (summaryEverValid \/ (summarySlot = "empty"))
    /\ UNCHANGED <<
        stateInitialized, adventureId, dbRecords, dbChapters, dbComplete,
        summaryReadySent, unsavedChapterStreamed, clientStaleOverwriteHappened,
        prematureRevealCrash, initSavePending, initSaveAmbiguousCommit
        >>

(*
 * choice_processor.py:132-152
 * User retries reveal_summary after a failed final save: reuses the in-memory
 * SUMMARY chapter without duplicating it, saves is_complete=TRUE, sends summary_ready.
 *)
RetryRevealSummarySaveSucceeds ==
    /\ stateInitialized
    /\ ~initSavePending
    /\ adventureId = "assigned"
    /\ serverChapters = StoryLength + 1
    /\ ~summaryReadySent
    /\ dbChapters' = StoryLength + 1
    /\ dbComplete' = TRUE
    /\ summaryReadySent' = TRUE
    /\ UNCHANGED <<
        stateInitialized, adventureId, serverChapters, dbRecords,
        summarySlot, summaryEverValid, bgSummaryPending,
        unsavedChapterStreamed, clientStaleOverwriteHappened,
        prematureRevealCrash, initSavePending, initSaveAmbiguousCommit
        >>

Done ==
    /\ summaryReadySent
    /\ UNCHANGED vars

Next ==
    \/ StartInitialSave
    \/ InitialSaveAmbiguousTimeout
    \/ InitialSaveSucceeds
    \/ InitialSaveExhaustsRetries
    \/ AdvanceChapter
    \/ BackgroundSummarySucceeds
    \/ BackgroundSummaryFails
    \/ RevealSummaryWithStaleClientState
    \/ RevealSummaryBeforeConclusion
    \/ RevealSummarySucceeds
    \/ RevealSummarySaveFails
    \/ RetryRevealSummarySaveSucceeds
    \/ Done

Spec == Init /\ [][Next]_vars

SingleRecordPerAdventure ==
    dbRecords <= 1

ServerStateAuthoritative ==
    ~clientStaleOverwriteHappened

SummaryOnlyAfterConclusion ==
    /\ ~prematureRevealCrash
    /\ summaryReadySent =>
        /\ dbComplete
        /\ dbChapters = StoryLength + 1
        /\ serverChapters = StoryLength + 1

ValidSummaryNeverClobbered ==
    ~(summaryEverValid /\ summarySlot = "fallback")

NoUnsavedChapterProgress ==
    ~unsavedChapterStreamed

====
