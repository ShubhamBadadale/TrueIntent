# Combined Fraud Analysis

The default portal tab accepts optional transaction/call context, pasted text,
a screenshot and a suspicious URL. Individual link, message and transaction
benchmark tabs remain available.

Text and URL evidence use POST /check-combined. Screenshots first use the existing
POST /check-message image route; only successful readable OCR text is joined to
pasted text and submitted to /check-combined. An unreadable/failed screenshot
stops the workflow rather than silently issuing a partial low-risk result.

Transaction details and active-call status are local display context, explicitly
excluded from scoring and never sent as model inputs. INR transaction scoring
remains disabled after the Module A correctness fix. Context-only submissions
display Unable to assess with no numeric score. No ML training is changed.

The results show the backend's overall tier/index, separate URL and message
indices when available, transaction risk as unavailable, reasons, scoring
limitations, extracted screenshot text, submitted context and a safety action.
Message risk may already include embedded URLs; module scores are not independent
probabilities. Existing backend fusion behavior is unchanged.

Validation covers empty submissions, finite positive amounts, nonnegative whole
transfer counts, HTTP(S) URLs and supported screenshots up to 10 MB. Forms disable
editing while running, show the current stage, clear stale results on edits and
surface network/API/OCR failures. Clear all and Remove screenshot support retries.

Verification: npm test, npm run build, npm run lint in frontend; pytest tests/backend
tests/test_integration.py (or the full tests directory) from the repository root.
