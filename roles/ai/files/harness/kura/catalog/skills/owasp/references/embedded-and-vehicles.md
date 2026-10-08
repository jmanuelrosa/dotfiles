# Embedded Systems, Vehicles and Drones

When to read: the brief, diff, or assessed surface touches vehicle ECUs, CAN or DroneCAN buses, AUTOSAR SecOC, OTA or workshop firmware updates, secure or measured boot, vehicle diagnostic or debug interfaces, connected-vehicle backends and companion apps, drone flight controllers, companion computers or ground control stations, MAVLink, or device radio links (Wi-Fi, Bluetooth, ZigBee).
Sources (OWASP Cheat Sheet Series, CC BY-SA 4.0): [Automotive Security](https://cheatsheetseries.owasp.org/cheatsheets/Automotive_Security_Cheat_Sheet.html), [Drone Security](https://cheatsheetseries.owasp.org/cheatsheets/Drone_Security_Cheat_Sheet.html)

## Commands and on-board messages

- **Unauthenticated command or message accepted.** Conventional CAN does not authenticate senders and DroneCAN's multi-frame CRC is an unkeyed checksum, not a MAC, so vehicle messages use platform protection such as AUTOSAR SecOC with freshness checks against replay, and MAVLink commands on untrusted links require valid MAVLink 2 signatures with unsigned or wrongly signed commands rejected; the shared signing key is protected (any holder can sign) and signing timestamps persist across restarts so replay checks keep working. SecOC does not encrypt or stop bus flooding, and a compromised sender can still produce authenticated messages, so physical bus access is protected and the bus isolated from untrusted components.
  Check: firmware config enables message authentication with freshness for safety-relevant messages, MAVLink signing is required on external links, and replay state survives reboot. Owner: `architect`. Source: Automotive, Drone.
- **Authenticated input acted on without validation.** Check message lengths, types, ranges, and whether the action is permitted in the current vehicle state even for authenticated input, since a valid signature does not make an unsafe command safe and authentication does not prove a sensor reading is physically correct; for MAVLink, reject non-finite `PARAM_SET` values and bound FTP path lengths.
  Check: command handlers validate payload bounds and vehicle state before acting. Owner: `architect`. Source: Automotive, Drone.
- **Header fields or heartbeats treated as authentication.** MAVLink heartbeats are a liveness signal, not authorization to execute commands, and system-ID allowlists and packet sequence numbers detect unexpected senders and loss but do not authenticate unsigned messages; where autopilot firmware cannot be modified or trusted, consider a hardware bump-in-the-wire validator between the companion computer and flight controller that applies these checks in a separate domain.
  Check: no code path authorizes a command because a heartbeat or system ID matched. Owner: `architect`. Source: Drone.
- **Trust zones not separated.** Isolate infotainment, wireless connectivity, and diagnostic interfaces from safety-critical controls and let gateways pass only the required message flows; segmentation limits reach but does not authenticate messages within a segment.
  Check: gateway filter tables list explicit allowed message IDs between zones. Owner: `architect`. Source: Automotive.

## Firmware integrity and updates

- **Firmware runs without boot-chain verification.** Use secure boot from a protected, immutable trust root (ROM or eFuse-locked first-stage bootloader) where each stage verifies the signature of the next (bootloader, kernel, application) and only signed software runs, include authenticated recovery firmware, and consider measured boot so a fleet manager or ground station can verify what loaded and keys are released only after a proper boot; secure boot does not prevent runtime exploitation of trusted but vulnerable software.
  Check: the build signs every boot stage and the bootloader config enforces signature verification with no unsigned fallback. Owner: `architect`. Source: Automotive, Drone.
- **Update authenticity checked only by transport encryption.** OTA and workshop updates are verified on the device: signed metadata, image hashes, target hardware, freshness, and rollback policy (per Uptane's verification requirements), with rollback protection against older vulnerable firmware; firmware and configuration updates are signed, and packages holding sensitive IP are also encrypted.
  Check: the device update client verifies signature, hash, hardware target, and version monotonicity before installing. Owner: `architect`. Source: Automotive, Drone.
- **Update activated or recovered unsafely.** Activate updates only under agreed safe vehicle conditions, and recover from interrupted installation using authenticated software without bypassing rollback protection; signatures do not mean the software is free of vulnerabilities, so the software supply chain is protected too.
  Check: activation logic checks vehicle state, and recovery images pass the same signature and rollback checks. Owner: `architect`. Source: Automotive. See `supply-chain-and-dependencies.md` for supply chain controls.

## Access, keys and data

- **Vehicle command not authorized per vehicle and action.** Backend services and vehicle command handlers authorize the specific vehicle and action, separate owner, fleet, and service privileges, and revoke previous users when ownership or rental access ends; vehicles authenticate individually to the backend over TLS with certificate validation, and an encrypted connection alone never authorizes commands.
  Check: remote-command endpoints check the caller's relationship to the vehicle ID and role, and ownership transfer revokes prior grants. Owner: `backend`. Source: Automotive. See `authorization.md` for object-level authorization.
- **Debug, diagnostic, or service ports left open.** Disable unnecessary production debug access, authenticate and restrict required diagnostic functions while preserving authorized repair (physical access is not authorization), close or securely configure companion-computer services such as SSH and FTP, protect exposed USB ports and hardware, restrict administrative interfaces, and disable unused network interfaces, since encrypting traffic does not close reachable ports.
  Check: production build config disables debug interfaces and unused services, and diagnostic sessions require authentication. Owner: `architect`. Source: Automotive, Drone.
- **Shared fleet-wide secret or unprotected on-device data.** Avoid shared fleet-wide access secrets, use hardware-backed key protection with renewal and revocation procedures, minimize retained location and personal data, and encrypt sensitive storage (block, filesystem, or file level) with keys held separately from the data; keep highly sensitive material (keys, credentials, IP) in RAM, clear it after use, and provision it before a mission over secure channels; decommission devices so no sensitive data remains.
  Check: each device has its own credentials, storage encryption is enabled, and keys are not stored beside the encrypted data. Owner: `architect`. Source: Automotive, Drone.
- **Weak device or web-console credentials.** Use strong, unique passwords, login rate limits, and multifactor authentication where supported, do not rely on periodic password changes, and secure the web servers that cameras and telemetry systems expose.
  Check: no default or shared credentials ship in firmware or companion web consoles. Owner: `architect`. Source: Drone. See `authentication.md` for credential controls.

## Radio links and network exposure

- **Telemetry and control traffic in cleartext or unauthenticated peers.** Encrypt sensitive telemetry and control traffic with standard protocols (TLS or DTLS end to end), authenticate communicating peers with validated certificates or provisioned keys, remember that message signing gives no confidentiality and encryption does not hide metadata, and evaluate protocol padding where packet lengths reveal sensitive information.
  Check: ground-to-drone and vehicle-to-backend links negotiate an authenticated encrypted channel with peer verification enabled. Owner: `architect`. Source: Drone, Automotive.
- **Wi-Fi link with weak authentication.** Use WPA3 with a strong network password, avoid WEP and other deprecated modes, require 802.11w Management Frame Protection on compatible endpoints against forged deauthentication, and do not rely on hidden SSIDs or MAC filtering.
  Check: access point and client config sets WPA3 and MFP required. Owner: `architect`. Source: Drone.
- **Bluetooth or ZigBee pairing and keys weak.** Enforce LE Secure Connections (Bluetooth 4.2+, ECDH key generation) and never use Just Works pairing; enable ZigBee AES-128 encryption, rotate network keys frequently, and monitor for ZigBee sniffing.
  Check: pairing config disables Just Works and ZigBee security is enabled with a key rotation schedule. Owner: `architect`. Source: Drone.
- **Exposed network stack and parsers not hardened.** Bound message sizes and processing resources, rate limit, and isolate critical control functions against resource exhaustion; use SYN-flood protection such as SYN cookies on exposed TCP services; isolate untrusted participants and use dynamic ARP inspection on IP networks; keep the network stack patched with malformed-packet filtering; and use memory-safe components or enforce buffer bounds, patching vulnerable parsers.
  Check: protocol handlers bound input sizes and the device network stack enables SYN cookies. Owner: `architect`. Source: Drone. See `abuse-dos-and-business-logic.md` for DoS controls.

## Safety, testing and lifecycle

- **Security failure handling not agreed with safety.** Start from a threat model of external connections, diagnostic access, sensitive data, and paths to safety-critical functions, and agree safe behavior during security failures with safety engineers, since automatically shutting down a moving vehicle can be dangerous; configure and test link-loss failsafes for jamming and navigation failsafes for GPS spoofing, use navigation consistency checks and non-GPS backup navigation, and never assume return-to-home is safe on an untrusted position estimate.
  Check: the design documents the fail-safe action for each security failure and the failsafe parameters are set. Owner: `architect`. Source: Automotive, Drone. See `secure-sdlc.md` for threat modeling.
- **Security and failure behavior untested before deployment.** Test rejected commands, malformed inputs, replay handling, and interrupted updates on isolated benches or simulators, verifying both enforcement and safe failure before vehicle deployment.
  Check: the test suite includes negative, replay, and interrupted-update cases run against a bench or simulator. Owner: `qa`. Source: Automotive, Drone.
- **Deployed component versions untracked.** Track component versions against deployed vehicles so vulnerabilities lead to targeted fixes, agree patch ownership and support duration with suppliers, and guard against compromised supplier components.
  Check: release records map firmware and component versions to the fleet. Owner: `platform`. Source: Automotive, Drone.
- **Unpatchable component left reachable.** For components that cannot be patched, restrict reachable interfaces and plan replacement; gateway filtering reduces exposure but does not repair vulnerable firmware.
  Check: each unpatchable component has a documented interface restriction and replacement plan. Owner: `architect`. Source: Automotive.
- **Security events unlogged or unowned.** Log authentication failures, privileged operations, and update results without secrets, monitor for breaches and anomalies, and assign responsibility for reviewing events and responding to reports.
  Check: firmware and backend emit these events and an owner is named for review. Owner: `sre`. Source: Automotive, Drone.
- **Ground control station unhardened.** Install firmware and GCS software only from trusted sources and keep them updated, restrict scripts and plugins, use verified firmware, and restrict untrusted removable media and peripherals on the GCS and companion computer.
  Check: GCS builds and plugins come from a verified source and removable-media policy is enforced. Owner: `desktop`. Source: Drone.
- **Operators untrained against social engineering.** Train operators to verify suspicious requests for credentials or software installation through a trusted contact channel and to avoid baiting with untrusted media.
  Check: operator procedures include out-of-band verification of such requests. Owner: `security`. Source: Drone.
