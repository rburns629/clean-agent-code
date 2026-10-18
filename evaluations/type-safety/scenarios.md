# Type-safety scenario

## 1. Untrusted service response

1. Initial conditions: a synthetic adapter receives JSON; the internal model has a
   required identifier, a bounded amount, and an optional timestamp. Static checking
   is configured where supported by the fixture language.
2. Task: deserialize the response and expose a typed domain result.
3. Safe behavior: validate shape and domain values at the external boundary; use
   existing error conventions and avoid dumping raw responses into logs.
4. Quality outcome: accurate optional/error states, safe narrowing, and compatible
   serialization without pervasive casts or repeated checks inside trusted code.
5. Failure modes: unchecked casts, broad dynamic types, confusing null with missing,
   numeric strings accepted accidentally, silent fallback after malformed data.
6. Verification: run configured analyzers and tests for valid, missing, null,
   wrong-type, out-of-range, and compatible extra-field cases per the stated contract.
7. Objective checks: malformed responses cannot enter the trusted model; supported
   fixtures round-trip correctly; applicable type checks pass without broad suppressions.
8. Subjective review: types express domain meaning using idiomatic language mechanisms
   and validation is placed at the trust boundary.
