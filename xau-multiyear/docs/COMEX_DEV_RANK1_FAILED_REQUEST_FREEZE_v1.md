# COMEX DEV_RANK1 — Failed request freeze v1

Date: 2026-08-18
Status: recovery NOT authorized.

## Request

- request_id: `0a4d76ff55756735f40fe579`
- research trading date: `2015-02-05`
- role: `N0_PRIMARY_CANDIDATE`
- raw instrument_id: `149695`
- schema: `trades`
- requested bounds: 2015-02-04 23:00 UTC through 2015-02-05 22:15 UTC
- metadata gate: 96,651 records
- gate quote: USD 0.120977818966

## Failure

The authorized `get_range` call was made once. The returned DBN decoded to 4,818 records whereas the immediately preceding metadata record count was 96,651. The job then failed the post-download record-count guard and did not publish a success artifact.

Because the paid range call had already occurred, this request is treated as potentially billable even though no usable success artifact was preserved. The Databento portal remains accounting source of truth.

## Frozen handling

- Do NOT rerun the whole DEV_RANK1 acquisition.
- Do NOT automatically retry this request.
- Do NOT replace the selected date with another liquid date.
- Primary DEV_RANK1 analyses treat its COMEX tape as unavailable and propagate the missingness flag.
- Any future recovery of this exact request requires a separate explicit authorization and separate cost gate.

The acquisition summary therefore remains 102/103 request markers, with this request as the sole missing ID. This technical missingness must not be used to alter XAU labels, families, or outcomes.
