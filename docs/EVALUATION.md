# Evaluation

Run `make eval` to execute the offline suite and generate [JSON](../evidence/offline-evaluation.json) and [readable results](../evidence/offline-evaluation.md). Counts come from pytest JUnit output, not hand-entered badges. Each report records commit/dirty status, implementation/lock/prompt hashes, exact test nodes and durations. Test-node counts are not scenario denominators or recovery rates.

The actual [local demo](../evidence/local-demo.json) uses independent persistent provider state and SIGKILL. The oracle deliberately detects a second allowed $30 partial refund with another key. F05/F08/F26 use subprocess behavior. Stripe pagination tests exercise the installed SDK with an isolated HTTP transport including a failing later page; these are not Stripe network calls.

Connected service actions, genuine live-model outputs and connected crash evidence: **NOT_RUN**, blocked by missing private configuration. `make submission-check` returns nonzero. `make review-check` checks offline evidence consistency only. The negative gate suite checks missing app/video, wrong mode/count, stale hashes, broken paths and duplicate-refund records. A passed consistency checker cannot authenticate provider history.

Full v3 acceptance remains unclaimed. Consult status/limitations for operational requirements not yet complete. Two dependency deprecation warnings currently arise from the FastAPI/Starlette test client stack.
