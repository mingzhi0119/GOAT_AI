# Desktop Cargo Audit Exceptions

> Last reviewed: 2026-04-11
> Applies to: `frontend/src-tauri/Cargo.lock`
> Review again by: 2026-07-31

These exceptions are temporary waivers for advisories currently pulled in by the Tauri 2 / WRY desktop stack. They are tracked in-repo so the `desktop-supply-chain` CI gate can remain blocking without forcing silent local bypasses.

## Rules

- Every ignored advisory must stay documented here with a concrete upstream reason.
- Exceptions expire when the dependency path is removed, upgraded away, or the review date passes.
- New ignores must update this document and the CI command in the same change.

## Current exceptions

### GTK3 / Linux desktop stack inherited from Tauri / WRY

- `RUSTSEC-2024-0411`: `gdkwayland-sys` is inherited from the current Linux GTK3 path in `tauri-runtime-wry`; revisit when the desktop shell moves off this chain.
- `RUSTSEC-2024-0412`: `gdk` is inherited from the same GTK3 chain.
- `RUSTSEC-2024-0413`: `atk` is inherited from the same GTK3 chain.
- `RUSTSEC-2024-0414`: `gdkx11-sys` is inherited from the same GTK3 chain.
- `RUSTSEC-2024-0415`: `gtk` is inherited from the same GTK3 chain.
- `RUSTSEC-2024-0416`: `atk-sys` is inherited from the same GTK3 chain.
- `RUSTSEC-2024-0417`: `gdkx11` is inherited from the same GTK3 chain.
- `RUSTSEC-2024-0418`: `gdk-sys` is inherited from the same GTK3 chain.
- `RUSTSEC-2024-0419`: `gtk3-macros` is inherited from the same GTK3 chain.
- `RUSTSEC-2024-0420`: `gtk-sys` is inherited from the same GTK3 chain.
- `RUSTSEC-2024-0429`: `glib` unsoundness is inherited from the same GTK3 chain.
- `RUSTSEC-2024-0370`: `proc-macro-error` is still pulled transitively via the same GTK macro stack.

Exit condition:
Move to a Tauri / WRY dependency set that no longer relies on the GTK3 bindings chain, or narrow supported desktop targets enough that these crates are no longer shipped.

### Tauri HTML / URL parsing transitive dependencies

- `RUSTSEC-2025-0057`: `fxhash` is inherited via `selectors` -> `kuchikiki` -> `tauri-utils`.
- `RUSTSEC-2025-0075`: `unic-char-range` is inherited via `urlpattern` -> `tauri-utils`.
- `RUSTSEC-2025-0080`: `unic-common` is inherited via `urlpattern` -> `tauri-utils`.
- `RUSTSEC-2025-0081`: `unic-char-property` is inherited via `urlpattern` -> `tauri-utils`.
- `RUSTSEC-2025-0098`: `unic-ucd-version` is inherited via `urlpattern` -> `tauri-utils`.
- `RUSTSEC-2025-0100`: `unic-ucd-ident` is inherited via `urlpattern` -> `tauri-utils`.
- `RUSTSEC-2026-0097`: `rand` unsoundness is inherited via `phf` / `kuchikiki` code generation pulled by `tauri-utils`.

Exit condition:
Upgrade to a `tauri-utils` / `kuchikiki` / `urlpattern` chain that removes these advisories, or replace the affected parsing path upstream.
