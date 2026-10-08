# C, C++ and Objective-C toolchain hardening

When to read: the brief, diff, or assessed surface touches the build of C, C++ or Objective-C code: `CFLAGS` / `CXXFLAGS` / `LDFLAGS`, Makefiles, Autotools (`configure.ac`, `Makefile.am`, `m4`), CMake or Xcode build settings, Visual Studio project properties, preprocessor defines (`NDEBUG`, `DEBUG`, `_FORTIFY_SOURCE`, `_CRT_SECURE_NO_WARNINGS`), vendored native libraries such as OpenSSL or SQLite, or `assert` and error handling in native code.
Sources (OWASP Cheat Sheet Series, CC BY-SA 4.0): [C-Based Toolchain Hardening Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/C-Based_Toolchain_Hardening_Cheat_Sheet.html)

## Contents

- Exploit mitigations: GCC, Clang and Binutils
- Exploit mitigations: Visual Studio
- Build configuration integrity
- Preprocessor and third-party library hardening
- Production failure behavior and assertions
- Unsafe conversions and ignored results
- Compiler warnings and static analysis
- Debug, test and runtime diagnostics

## Exploit mitigations: GCC, Clang and Binutils

- **Stack protector missing or partial.** Stack Smashing Protector adds a guard that detects stack buffer overflows; build with `-fstack-protector-all` (guards all objects) rather than relying on `-fstack-protector` (only high-risk objects such as C strings), which is all many distributions enable by default (`gcc -dumpspecs` shows it).
  Check: release `CFLAGS` / `CXXFLAGS` contain `-fstack-protector-all` (or a documented reason for the weaker variant) and nothing later adds `-fno-stack-protector`. Owner: `platform`. Source: C-Based Toolchain Hardening.
- **Program built without PIE.** Without position independence ASLR cannot relocate the executable; programs need both `-fPIE` (compiler) and `-pie` (linker, Binutils 2.16), and libraries both `-fPIC` and `-shared`.
  Check: executable targets compile with `-fPIE` and link with `-pie`; shared library targets use `-fPIC` and `-shared`. Owner: `platform`. Source: C-Based Toolchain Hardening.
- **Executable stack or heap.** Data execution is the norm on Linux unless the ELF headers say otherwise; link with `-Wl,-z,noexecstack` and `-Wl,-z,noexecheap` (Binutils 2.14) to mark `PT_GNU_STACK` and `PT_GNU_HEAP` non-executable.
  Check: `LDFLAGS` include both `-z` options and no object or flag (such as nested-function trampolines) re-enables an executable stack. Owner: `platform`. Source: C-Based Toolchain Hardening.
- **GOT and PLT left writable after load.** Link with `-Wl,-z,relro` and `-Wl,-z,now` (Binutils 2.15) to remediate Global Offset Table and Procedure Linkage Table attacks.
  Check: `LDFLAGS` include `-z,relro` and `-z,now`. Owner: `platform`. Source: C-Based Toolchain Hardening.
- **Shared objects loadable and dumpable by an attacker.** Link with `-Wl,-z,nodlopen` and `-Wl,-z,nodump` (Binutils 2.10) to reduce an attacker's ability to load, manipulate and dump shared objects.
  Check: `LDFLAGS` include both options where the binary does not need to be `dlopen`ed. Owner: `platform`. Source: C-Based Toolchain Hardening.
- **Release build without `_FORTIFY_SOURCE`.** Release builds define `_FORTIFY_SOURCE=2` on Linux and `_FORTIFY_SOURCE=1` on Android (4.2 and above); undefining it (`-U_FORTIFY_SOURCE`) is a security defect.
  Check: release defines include `_FORTIFY_SOURCE` at the platform's level and no flag undefines it. Owner: `platform`. Source: C-Based Toolchain Hardening.
- **Stack pointer can jump past the guard page.** `-fstack-check` stops the stack pointer moving into another memory region without touching the stack guard page, at some cost (it touches each page with a 4K stride).
  Check: `-fstack-check` is enabled, or its omission is a recorded performance decision. Owner: `platform`. Source: C-Based Toolchain Hardening.
- **Speculative-execution flags assumed to cover every variant.** On x86 choose mitigations for the target CPU and OS: `-mindirect-branch=thunk` and `-mfunction-return=thunk` (GCC 7.3, 8.1) implement retpoline, which mitigates specific Spectre variant 2 paths only; follow current platform guidance rather than assuming they cover every Spectre variant or Meltdown.
  Check: x86 builds that need these mitigations set both flags and reference the platform guidance they follow. Owner: `platform`. Source: C-Based Toolchain Hardening.
- **Hardening flags never verified on the produced binary.** Hardening must be applied at configure and build time because adding it after the fact is difficult to impossible on some platforms (for example statically linked Linux programs); verify the result with `checksec.sh` on Linux and BinScope on Windows.
  Check: the release pipeline runs a binary hardening check (checksec, BinScope or equivalent) on shipped artifacts. Owner: `platform`. Source: C-Based Toolchain Hardening.

## Exploit mitigations: Visual Studio

- **`/GS` missing or weakened.** `/GS` places a security cookie before the return address to detect stack buffer overruns; it is skipped for frames with no buffer, with optimizations disabled, or in naked functions and inline assembly, and `#pragma strict_gs_check(on)` applies stack protection aggressively and is recommended, sparingly, for high-risk files such as those parsing internet input.
  Check: project properties enable `/GS`, and input-parsing translation units use `strict_gs_check(on)`. Owner: `platform`. Source: C-Based Toolchain Hardening.
- **DEP or ASLR not opted in.** Link with `/NXCOMPAT` (Data Execution Prevention) and `/DYNAMICBASE` (Address Space Layout Randomization).
  Check: linker settings include both switches for every executable and DLL. Owner: `platform`. Source: C-Based Toolchain Hardening.
- **SEH overwrites not remediated.** Link with `/SafeSEH` for safe structured exception handling.
  Check: linker settings include `/SAFESEH` for applicable targets. Owner: `platform`. Source: C-Based Toolchain Hardening.
- **Control Flow Guard half-configured.** Control Flow Guard checks that indirect calls land on legal targets (also against heap sprays and no-op sleds); `/d2guard4` (compiler) and `/guard:cf` (linker) must be used together (Visual Studio 2015).
  Check: both the compiler and linker switches are present, not one alone. Owner: `platform`. Source: C-Based Toolchain Hardening.
- **SDL checks off.** `/sdl` adds Security Development Lifecycle checks, including security-relevant warnings as errors and additional secure code generation.
  Check: `/sdl` is enabled in all configurations. Owner: `platform`. Source: C-Based Toolchain Hardening.

## Build configuration integrity

- **User-supplied hardening flags discarded by the build.** Many projects ignore the user's command line, so `make CFLAGS="-fPIE" LDFLAGS="-pie -z,noexecstack"` silently yields neither defense; merge project flags with user flags so the user's come last (`override CFLAGS := $(PROJECT_CFLAGS) $(CFLAGS)`, likewise `CXXFLAGS` and `LDFLAGS`), and when Autotools ignores requested flags fix the `m4`, `Makefile.in` or `Makefile.am` sources.
  Check: the build files append rather than replace `CFLAGS`, `CXXFLAGS` and `LDFLAGS`, and generated makefiles carry the hardening flags. Owner: `platform`. Source: C-Based Toolchain Hardening.
- **Objects reused across build configurations.** Make compares timestamps, not flags, so switching from debug to release can ship debug-instrumented objects (and an `assert` that aborts); use separate build directories for debug, test and release.
  Check: each configuration builds into its own directory (VPATH or out-of-tree builds). Owner: `platform`. Source: C-Based Toolchain Hardening.
- **Hardening dropped to the lowest common denominator.** Compiler and linker defenses are not on by default and Autotools rarely enables them; ship with every available defense in force and let platforms lacking a feature edit the build, rather than weakening the posture for everyone.
  Check: the default build enables the full flag set, with feature detection adding flags rather than removing them. Owner: `platform`. Source: C-Based Toolchain Hardening.
- **`NDEBUG` and `DEBUG` ambiguous.** Release builds define `NDEBUG` and not `DEBUG`; debug builds define `DEBUG` and not `NDEBUG` (`-DDEBUG=1 -UNDEBUG`), for all code including bundled libraries; a shared configuration header raises `#error` when both are defined and treats neither as release.
  Check: release flags carry `-DNDEBUG` without `DEBUG`, and a common header enforces the both-defined error. Owner: `platform`. Source: C-Based Toolchain Hardening.

## Preprocessor and third-party library hardening

- **Security-weakening macros defined.** Defining `_CRT_SECURE_NO_WARNINGS=1`, `_SCL_SECURE_NO_WARNINGS`, `_ATL_SECURE_NO_WARNINGS` or `STRSAFE_NO_DEPRECATE` on Windows, or undefining `_FORTIFY_SOURCE` on Linux, should trigger a security defect.
  Check: no build file or header defines these macros or passes `-U_FORTIFY_SOURCE`. Owner: `platform`. Source: C-Based Toolchain Hardening.
- **Microsoft CRT, ATL and SafeInt hardening macros missing.** Debug builds define `_DEBUG=1`, `STRICT`, `_SECURE_SCL=1`, `_HAS_ITERATOR_DEBUGGING=1`, `_CRT_SECURE_CPP_OVERLOAD_STANDARD_NAMES=1` and `_CRT_SECURE_CPP_OVERLOAD_STANDARD_NAMES_COUNT=1`; release builds define `STRICT` and both overload macros; ATL/MFC define `_SECURE_ATL`, `_ATL_ALL_WARNINGS` and `_ATL_CSTRING_EXPLICIT_CONSTRUCTORS`, and SafeInt `SAFEINT_DISALLOW_UNSIGNED_NEGATION=1`, in both configurations.
  Check: the Windows project's preprocessor definitions per configuration include these macros. Owner: `platform`. Source: C-Based Toolchain Hardening.
- **Release logging and assertions left in mobile builds.** Release builds define `NS_BLOCK_ASSERTIONS=1` and define `NSLog(...)` to nothing on Cocoa/CocoaTouch, and define `LOGI(...)` to nothing on Android, preempting logging; Android debug builds define `NDK_DEBUG=1`.
  Check: release configurations carry these defines. Owner: `mobile`. Source: C-Based Toolchain Hardening.
- **Debug STL checking misapplied.** Debug builds define `_GLIBCXX_DEBUG=1` and `_GLIBCXX_CONCEPT_CHECKS=1` on Linux (and `_STLP_DEBUG=1`, `_STLP_USE_DEBUG_LIB=1`, `_STLP_DEBUG_ALLOC=1`, `_STLP_DEBUG_UNINITIALIZED=1` with STLport); `_GLIBCXX_DEBUG` is ABI-incompatible with precompiled libraries such as distribution Boost, so compile those libraries with it or omit it.
  Check: debug defines include the checking macros and every linked C++ library is built with the same `_GLIBCXX_DEBUG` setting. Owner: `dx`. Source: C-Based Toolchain Hardening.
- **Third-party native libraries built with insecure defaults.** You are responsible for libraries you include (supply chain audits such as SP800-53 SA-12 cover them), so harden their build; for OpenSSL configure `-no-ssl2 -no-ssl3 -no-comp`, adding `-no-hw -no-engine -no-shared -no-dso` when hardware engines and dynamic loading are not used.
  Check: vendored OpenSSL build scripts pass these switches, and no `COMP_CTX_*` symbols exist in the built `libcrypto` (`OPENSSL_NO_COMP` is defined). Owner: `platform`. Source: C-Based Toolchain Hardening.
- **SQLite and SQLCipher built without data-protection macros.** Define `SQLITE_SECURE_DELETE` to zeroize deleted content (always in US Federal work, as FIPS 140-2 Level 1 requires zeroization), set `SQLITE_DEFAULT_FILE_PERMISSIONS=N` because the 0644 default gives everyone some access, and for SQLCipher define `SQLITE_HAS_CODEC=1` and `SQLITE_TEMP_STORE=3` to keep temporary tables in memory so no unencrypted data reaches disk.
  Check: the SQLite amalgamation build defines these macros in both debug and release. Owner: `platform`. Source: C-Based Toolchain Hardening.

## Production failure behavior and assertions

- **Release code asserts or auto-aborts.** Production hosts always run with `NDEBUG` defined, so they neither assert nor abort; auto-abort is not acceptable production behavior, and a program that wants a core dump creates one itself rather than crashing, so secrets are not written to the filesystem and mailed in plain text.
  Check: release paths contain no `assert`-then-`abort()` error handling and crash dumps are produced deliberately with controlled content. Owner: `backend`. Source: C-Based Toolchain Hardening.
- **Validation without a matching assert, or an assert without runtime handling.** Assert parameters on function entry, return values and program state; every `if` used for validation has an assert and every validation assert has an `if` that handles the failure in release.
  Check: each input-validation `if` is paired with an `ASSERT`, and no check exists only as an assert. Owner: `backend`. Source: C-Based Toolchain Hardening.
- **Debug assert that aborts instead of trapping.** Supply a project assert that raises `SIGTRAP` in debug builds (installing a `SIGTRAP` handler at startup only if none exists) and evaluates to `void` otherwise; on Windows install a handler with `_set_invalid_parameter_handler` (and possibly `set_unexpected` or `set_terminate`).
  Check: the project's `ASSERT` macro traps rather than calls `abort()` in debug and compiles away in release. Owner: `backend`. Source: C-Based Toolchain Hardening.

## Unsafe conversions and ignored results

- **Signed value cast to unsigned without a range test.** Signed-to-unsigned promotion makes `-1 > 1`; never cast blindly, range-test first (for example check a port is within 1 to 65535 before narrowing to `unsigned short`).
  Check: every cast flagged by `-Wconversion` / `-Wsign-conversion` is preceded by an explicit range check. Owner: `backend`. Source: C-Based Toolchain Hardening.
- **Numeric input parsed with `atoi` and friends.** `atoi` silently fails; parse with a function that reports failure, check the failure flag, then range-check the value.
  Check: no `atoi` / `atol` on external input; parsing checks for failure and bounds. Owner: `backend`. Source: C-Based Toolchain Hardening.
- **Return values ignored or cast to `void`.** Ignoring results turns errors into silent truncations, such as an `snprintf` path that is then `open`ed even though it may name an attacker-controlled file; check `snprintf` for `-1` and for a result `>= sizeof(buffer)` and handle both.
  Check: `snprintf` and similar calls have their return value checked for error and truncation before the output is used. Owner: `backend`. Source: C-Based Toolchain Hardening.
- **Code that only works with `-fno-strict-overflow` or `-fwrapv`.** These flags stop the compiler removing overflowing or wrapping statements; a program that needs them is likely relying on illegal overflow, so use safe-iop in C or SafeInt in C++.
  Check: when either flag is present, arithmetic on untrusted sizes uses checked-integer helpers. Owner: `backend`. Source: C-Based Toolchain Hardening.

## Compiler warnings and static analysis

- **GCC warning set too narrow.** Enable `-Wall -Wextra -Wconversion -Wsign-conversion -Wcast-align -Wformat=2 -Wformat-security -fno-common -Wmissing-prototypes -Wmissing-declarations -Wstrict-prototypes -Wstrict-overflow` (GCC 4.2) and `-Wtrampolines` (GCC 4.3); for C++ add `-Woverloaded-virtual -Wreorder -Wsign-promo -Wnon-virtual-dtor -Weffc++`, and for Objective-C `-Wstrict-selector-match -Wundeclared-selector`.
  Check: the shared warning flags include this set for the languages in the project. Owner: `dx`. Source: C-Based Toolchain Hardening.
- **Clang and Visual Studio analysis unused.** Use Clang's `-Weverything` regularly (for example in production builds) with non-spurious issues as a quality gate, plus the Clang Static Analyzer; under Visual Studio use `/W4` or `/Wall` and `/analyze`; compiler analysis does not catch tainted data such as SQL injection, which needs a data-flow or taint analysis tool.
  Check: CI runs a build with `-Weverything` or `/Wall` plus the static analyzer, and gates on new findings. Owner: `dx`. Source: C-Based Toolchain Hardening.
- **Warnings turned off instead of suppressed.** Do not turn warnings off; reduce noise only with targeted switches (`-Wno-unused-parameter`, `-Wno-type-limits` on GCC 4.3, `-Wno-tautological-compare` on Clang) and silence an unused parameter at its use site with a `(void)x` macro.
  Check: no blanket `-w` or broad `-Wno-*` beyond these appears, and suppressions are local. Owner: `dx`. Source: C-Based Toolchain Hardening.

## Debug, test and runtime diagnostics

- **Debug build without full instrumentation.** Debug builds use `-O0 -g3 -ggdb` (or `-Og` with `-g`; `-O1` where analysis warnings are needed; `/Od` on Windows) and `-fno-omit-frame-pointer`, and integrate diagnostics such as `dmalloc`, AddressSanitizer (`-fsanitize=address`, GCC 4.8), ThreadSanitizer (`-fsanitize=thread`) and Clang's `-fsanitize=integer` and `-fsanitize=shift`; code checked in without debug instrumentation is fixed or rejected.
  Check: a debug or CI configuration builds with the sanitizers and debug flags and runs the tests under them. Owner: `dx`. Source: C-Based Toolchain Hardening.
- **Release symbols shipped or discarded.** Release builds use `-O2` or `-Os` (`/Ox`, `/O2` or `/Os` on Windows) with `-g2`, then strip debug information from the shipped binary and retain it for symbolicating field crash reports.
  Check: the release pipeline strips binaries and archives the separated symbols. Owner: `platform`. Source: C-Based Toolchain Hardening.
- **Test configuration skips non-public interfaces and negative tests.** The test build is a release build that exposes every interface (`-Dprotected=public -Dprivate=public`, `visibility("default")` instead of `"hidden"`), and negative self-tests verify the program fails gracefully with no crash and no memory corruption.
  Check: a test configuration exists and the suite contains negative tests against internal interfaces. Owner: `qa`. Source: C-Based Toolchain Hardening.
- **Platform runtime diagnostics unused during development.** Enable Xcode scheme diagnostics (Scribble, Guard Edges, Guard Malloc, Zombies; some are simulator-only) and Visual Studio Managed Debugging Assistants while developing.
  Check: shared Xcode schemes enable the memory diagnostics for the debug run action. Owner: `dx`. Source: C-Based Toolchain Hardening.
- **Windows exploit protection not configured at runtime.** Configure Windows Defender Exploit Guard (the EMET replacement) and set process mitigation policies with the `ProcessMitigations` PowerShell module or Group Policy.
  Check: deployment configuration for Windows hosts applies exploit protection settings for the shipped executables. Owner: `platform`. Source: C-Based Toolchain Hardening.
