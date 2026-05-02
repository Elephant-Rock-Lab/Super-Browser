# Domain Pack: Remote Desktop & Screen Sharing

> **Version**: v1.0
> **Taxonomy Coverage**: All 10 categories
> **Pillar Count**: 20
> **Derived from**: Generic taxonomy v1.0, specialized for P2P remote desktop platforms, VPN mesh networking, protocol interop, and roaming

## Overview

Specializes the generic taxonomy for remote desktop and screen sharing systems — software that captures a host's display, transmits it over a network, and renders it on a remote viewer while relaying input (mouse, keyboard, clipboard) back to the host. Covers P2P and relayed architectures, cross-platform capture/encoding, low-latency video pipelines, end-to-end encryption, VPN mesh networking with roaming, protocol interoperability (SSH, RDP, VNC), and viewer UI/interaction design.

## Pillar Definitions

### 1. Screen Capture

**Generic category**: Perception & Input
**Types**: Full-screen capture, region capture, multi-monitor enumeration, differential/dirty-rect capture
**Look for**:
- Platform capture backends — DXGI/Desktop Duplication (Windows), X11/XShm/XRandR (Linux), CGWindowListCreateImage (macOS), Wayland pipewire/xdg-desktop-portal
- Multi-monitor handling — enumeration, selection, dynamic display change detection
- Frame timing — capture interval, VSync alignment, frame skipping strategies
- Dirty-rect / damage tracking — only re-encoding changed regions
- Cursor capture — composited into frame vs. separate cursor overlay channel
- GPU-direct capture — capturing directly from GPU surfaces without CPU round-trip
- Permission handling — screen recording permission prompts (macOS, Wayland)
**Extract**: Capture loop implementations, platform API call sequences, frame pool/recycling strategies, monitor enumeration data structures
**Intrinsic value indicators**: GPU-direct capture without CPU copy, dirty-rect with minimal overhead, adaptive capture rate based on content change

### 2. Video Encoding

**Generic category**: Processing & Logic
**Types**: Software encoding (x264, x265, libvpx, libaom), hardware encoding (NVENC, QSV, VAAPI, VideoToolbox), raw/uncompressed passthrough
**Look for**:
- Codec selection strategies — H.264/H.265/VP8/VP9/AV1, when to use which
- Latency-optimized presets — zerolatency tuning, baseline/main/high profile, preset selection (ultrafast vs. quality)
- Rate control — CBR, VBR, CRF, capped quality factor. How is target bitrate determined?
- Resolution change handling — encoder recreation on the fly, resolution negotiation
- Keyframe management — IDR interval, keyframe-on-request for new viewers
- Encoding thread pool configuration — thread count, slice-based parallelism
- GPU hardware encoding pipelines — NVENC session management, DMA buffer import
- Bandwidth estimation informing encoding parameters
**Extract**: Encoder initialization parameters, rate control formulas, resolution change handling code, keyframe request handling
**Intrinsic value indicators**: Hardware encoder with zero-copy GPU pipeline, adaptive CRF based on network conditions, per-viewer encoding with shared pre-encoding stage

### 3. Video Decoding & Rendering

**Generic category**: Processing & Logic
**Types**: Software decoding (FFmpeg libavcodec), hardware decoding (DXVA2, VAAPI, VideoToolbox), browser decoding (WebCodecs)
**Look for**:
- Decoder initialization and format negotiation — codec capability exchange, fallback chains
- Hardware-accelerated decode — DXVA2/D3D11VA (Windows), VAAPI/VDPAU (Linux), VideoToolbox (macOS)
- Browser decode — WebCodecs VideoDecoder, codec string negotiation, MSE fallback
- Pixel format conversion — YUV→RGBA conversion (sws_scale, shader-based, GPU-accelerated)
- Frame rendering — OpenGL/DirectX/Metal/Cairo/Skia rendering paths, vsync alignment
- Frame buffer management — double/triple buffering, frame pool recycling
- Decoding error recovery — corrupt frame handling, keyframe request on decode failure
- Frame timing and synchronization — timestamp-based presentation, frame pacing
**Extract**: Decoder factory patterns, pixel format conversion code, rendering pipeline setup, error recovery logic
**Intrinsic value indicators**: Zero-copy GPU decode-to-render pipeline, hardware decode with direct scanout, adaptive decode thread count

### 4. Remote Input

**Generic category**: Perception & Input
**Types**: Mouse injection, keyboard injection, touch/gesture injection, gamepad support
**Look for**:
- Platform input injection — SendInput/user32 (Windows), XTest (Linux), CGEvent (macOS)
- Input event marshaling — wire format for mouse/keyboard events, coordinate normalization (0-65535 absolute vs. relative deltas)
- Input sanitization — bounds checking, rate limiting, input validation on the receiving side
- Modifier key handling — Ctrl/Alt/Shift state tracking, special key combinations (Ctrl+Alt+Del)
- International keyboard support — keyboard layout mapping, dead keys, IME handling
- Touch and gesture translation — touch-to-mouse event mapping, multi-touch forwarding
- Input latency optimization — batch processing, prediction, input prioritization over video frames
- UAC/elevation handling — input injection across privilege boundaries (Windows UAC, Linux root)
**Extract**: Input event wire format, platform injection call sequences, coordinate normalization formulas, input sanitization logic
**Intrinsic value indicators**: Input prediction to compensate for latency, multi-touch with gesture recognition, cross-privilege input injection

### 5. Clipboard Sync

**Generic category**: Perception & Input
**Types**: Text clipboard, image clipboard, file clipboard, cross-platform format negotiation
**Look for**:
- Clipboard monitoring — polling vs. OS notification (Windows clipboard chain, X11 selections, macOS NSPasteboard)
- Format negotiation — plain text, rich text, HTML, image (PNG/JPEG), file list
- Sync direction control — host-to-remote only, bidirectional, configurable per-session
- Conflict resolution — simultaneous clipboard changes on both sides
- Large payload handling — chunked transfer for images and files via clipboard
- Clipboard privacy — masking sensitive content, sandbox clipboard isolation
- Platform-specific quirks — X11 PRIMARY vs. CLIPBOARD selection, Windows clipboard formats
**Extract**: Clipboard monitor implementations, format conversion code, chunked transfer protocol, sync direction control logic
**Intrinsic value indicators**: Zero-loss format negotiation across platforms, efficient chunked transfer with progress, sandbox-aware clipboard isolation

### 6. Audio Forwarding

**Generic category**: Perception & Input
**Types**: System audio capture, microphone forwarding, bidirectional audio
**Look for**:
- Audio capture — WASAPI loopback (Windows), PulseAudio/PipeWire (Linux), CoreAudio (macOS)
- Audio codecs — Opus, AAC, FLAC, PCM. Latency vs. quality tradeoff per codec
- Audio synchronization — A/V sync strategies, jitter buffer, adaptive buffering
- Echo cancellation — AEC for bidirectional audio, when the same audio plays back
- Volume control — remote volume adjustment, mute support
- Multi-application audio — capturing specific application audio vs. system-wide
- Sample rate and channel negotiation — format exchange at session start
**Extract**: Audio capture loop code, codec initialization parameters, A/V sync algorithms, jitter buffer implementation
**Intrinsic value indicators**: Low-latency audio with echo cancellation, per-application audio capture, adaptive jitter buffer with network-aware sizing

### 7. P2P Connectivity & NAT Traversal

**Generic category**: Coordination + Goal & Planning
**Types**: Direct TCP/UDP, mDNS LAN discovery, STUN/TURN, ICE candidate exchange, hole punching, relay fallback
**Look for**:
- NAT traversal strategies — STUN binding, TURN relay, TCP/UDP hole punching, port prediction
- ICE-like candidate gathering — host candidates, server-reflexive candidates, relay candidates
- mDNS/service discovery — service type registration, TXT record metadata, browsing/lookup
- Connection racing — parallel connection attempts, fastest-wins selection
- P2P fallback to relay — timeout-based fallback, graceful degradation chain
- Connection keepalive — ping/pong intervals, idle timeout detection
- Reconnection — auto-reconnect with backoff, session resumption, state recovery
- Port mapping — UPnP/PCP/NAT-PMP for automatic port forwarding
**Extract**: Hole punching implementations, STUN message parsing, candidate exchange protocol, connection racing logic, reconnection state machines
**Intrinsic value indicators**: Multi-strategy NAT traversal with success rate tracking, predictive port allocation, graceful IPv4/IPv6 dual-stack handling

### 8. Relay Infrastructure

**Generic category**: Integration & Extension
**Types**: Signaling servers, TURN/relay servers, web bridges, connection brokers
**Look for**:
- Signaling protocol — registration, lookup, candidate exchange, relay coordination
- Relay/pipe matching — how two peers are matched through a relay, connection state management
- Web bridge architecture — browser-to-native bridging, protocol translation (WebSocket ↔ TCP)
- Load balancing — connection distribution, server selection, geo-routing
- Scalability — connection limits, resource management, per-connection state overhead
- Authentication at relay level — relay auth tokens, rate limiting, abuse prevention
- Deployment configuration — Docker, systemd, reverse proxy (Caddy/Nginx) integration
- Monitoring — connection metrics, uptime tracking, health check endpoints
**Extract**: Signaling message formats, pipe matching algorithms, web bridge protocol translation, deployment configurations
**Intrinsic value indicators**: Efficient pipe matching with O(1) lookup, zero-copy relay forwarding, web bridge with minimal latency overhead

### 9. Encryption & Key Exchange

**Generic category**: Governance & Quality
**Types**: E2E encryption, transport encryption, key exchange protocols, key management
**Look for**:
- Encryption protocols — Noise Framework, TLS, DTLS, SRTP, custom protocols
- Key exchange — Curve25519/X25519 DH, ECDH, key derivation functions (HKDF)
- Handshake patterns — Noise NK/XX/IK, TLS 1.3 0-RTT, pre-shared key modes
- Cipher suites — ChaCha20-Poly1305, AES-GCM. When is hardware acceleration used?
- Key rotation — session key rotation intervals, perfect forward secrecy
- Key storage — secure key storage, key derivation from passwords/seeds
- Certificate management — self-signed vs. CA, pinning, TOFU (trust-on-first-use)
- Zero-knowledge patterns — relay cannot decrypt traffic, server never sees plaintext
**Extract**: Handshake implementation code, key derivation functions, cipher initialization, key rotation logic, secure storage patterns
**Intrinsic value indicators**: Novel handshake with relay zero-knowledge, hardware-accelerated encryption, perfect forward secrecy with low overhead

### 10. Authentication & Authorization

**Generic category**: Governance & Quality
**Types**: Password authentication, token-based auth, public key auth, RBAC, session permissions
**Look for**:
- Password-based auth — HMAC challenge-response, SRP, PAKE (OPAQUE, SPAKE2)
- Token-based auth — JWT, session tokens, API keys
- Public key authentication — Ed25519 signature verification, authorized key lists
- Permission models — view-only, interactive input, file access, admin roles
- Session authorization — per-session consent, approval gates, confirmation dialogs
- Brute-force protection — rate limiting, lockout, exponential backoff
- Access control lists — IP allowlists, peer ID allowlists, group-based access
- Audit logging — connection logs, access attempts, permission changes
**Extract**: Challenge-response protocol implementations, permission schema definitions, consent UI flow, rate limiting algorithms
**Intrinsic value indicators**: PAKE-based password auth (no password-equivalent transmitted), granular per-session permissions, hardware key authentication

### 11. Peer Identity & Discovery

**Generic category**: Knowledge & Representation
**Types**: Peer IDs, public key infrastructure, address books, discovery protocols
**Look for**:
- Peer ID generation — from public key hash, from UUID, from human-readable name
- Identity key management — Ed25519/X25519 key pairs, key storage, key rotation
- Discovery mechanisms — mDNS, DHT, Rendezvous servers, manual address entry
- Address book — persistent peer storage, alias/nickname management, group management
- Peer verification — identity verification during handshake, TOFU policies
- Peer metadata — version, capabilities, online status, last-seen timestamps
- ID encoding — Base58, bech32, multihash. Human-readable vs. compact formats
**Extract**: Peer ID generation algorithms, key derivation chains, discovery protocol message formats, address book schemas
**Intrinsic value indicators**: Self-sovereign identity with key rotation, distributed discovery (DHT), capability-advertised peer metadata

### 12. Session Management

**Generic category**: Coordination
**Types**: Connection lifecycle, multi-viewer sessions, reconnection, session state
**Look for**:
- Connection state machines — states (connecting → authenticated → streaming → disconnected), transition triggers
- Multi-viewer support — shared encoder output to multiple viewers, per-viewer state, viewer addition/removal
- Concurrent session handling — one agent serving multiple simultaneous viewers
- Session persistence — saving/restoring session state, reconnection with state recovery
- Graceful disconnection — cleanup sequences, resource release, session end signaling
- View-only vs. interactive modes — mode negotiation, runtime mode switching
- Session timeout — idle timeout policies, automatic session termination
- Lock screen integration — remote lock, unlock, lock-on-disconnect
**Extract**: Connection state machine definitions, multi-viewer encoder sharing logic, reconnection state recovery code, session cleanup sequences
**Intrinsic value indicators**: Zero-interruption viewer addition with shared encoder, instant reconnection with cached state, dynamic mode switching without reconnect

### 13. Adaptive Streaming

**Generic category**: Autonomy & Scheduling + Adaptation & Learning
**Types**: Bitrate adaptation, quality adaptation, FPS adjustment, network-aware encoding
**Look for**:
- Bandwidth estimation — packet pair dispersion, ACK-based rate estimation, transport-layer signals (BBR, congestion windows)
- Quality adjustment strategies — CRF/target bitrate adjustment, resolution scaling, FPS reduction
- Network condition monitoring — latency tracking, packet loss detection, jitter measurement
- Congestion response — immediate quality drop vs. gradual adaptation, recovery behavior
- Frame dropping strategies — which frames to drop under pressure (B-frames vs. P-frames vs. all)
- Latency management — encoder latency budget, network latency compensation, decode latency tracking
- Statistics and diagnostics — real-time bitrate/latency/quality metrics, debug overlays
- Cold start optimization — initial quality ramp-up strategy, first-frame latency minimization
**Extract**: Bandwidth estimation algorithms, quality adjustment formulas, congestion response state machines, frame dropping decision logic
**Intrinsic value indicators**: BBR-based bandwidth estimation for real-time video, content-aware quality adaptation (text regions preserved), predictive quality ramp-up

### 14. File Transfer

**Generic category**: Data & Storage
**Types**: File upload/download, drag-and-drop, folder transfer, resumable transfer
**Look for**:
- Transfer protocols — in-band (same connection as video) vs. out-of-band (separate connection)
- Chunked transfer — block size, acknowledgment, ordered vs. unordered delivery
- Progress tracking — progress reporting, ETA calculation, speed display
- Resumable transfers — checkpoint/restart, partial file handling
- Drag-and-drop integration — file drop detection, temporary file handling
- Directory transfer — recursive traversal, preserving permissions/metadata
- Large file handling — streaming to disk, memory-mapped I/O, checksum verification
- Transfer queuing — multiple file queuing, priority, cancellation
**Extract**: Transfer protocol message formats, chunk management code, progress calculation, checksum verification logic
**Intrinsic value indicators**: Out-of-band parallel transfer not competing with video bandwidth, zero-copy file transfer via memory mapping, content-defined chunking for deduplication

### 15. Cross-Platform Build & Deployment

**Generic category**: Integration & Extension
**Types**: Platform abstraction, conditional compilation, packaging, deployment
**Look for**:
- Platform abstraction layers — interface-based platform services, build-tag-based selection
- CGo/FFI patterns — C interop for platform APIs, DLL/shared library management
- Build systems — Makefiles, CMake, xmake, cross-compilation toolchains
- Conditional compilation — Go build tags, Rust cfg attributes, C preprocessor
- Packaging — MSI/NSIS (Windows), deb/rpm (Linux), dmg/brew (macOS), Docker containers
- Dependency management — vendoring C libraries, static vs. dynamic linking
- Auto-update mechanisms — self-update, update checking, delta patches
- CI/CD pipelines — cross-platform build matrices, artifact distribution
- Deployment targets — native binary, Docker image, web application, portable/archive
**Extract**: Build configurations, platform interface definitions, packaging scripts, CI pipeline configurations, auto-update implementations
**Intrinsic value indicators**: Clean platform abstraction with zero-overhead dispatch, single-codebase native + web targets, automated cross-compile for all platforms

### 16. VPN & Virtual Networking

**Generic category**: Integration & Extension
**Types**: TUN/TAP virtual interfaces, IP-level tunneling, virtual LANs, site-to-site VPN, split tunneling
**Look for**:

- Virtual network interface creation — TUN/TAP device management, platform-specific creation (Windows TAP adapter, Linux tun device, macOS utun)
- IP-level tunneling — encapsulating IP packets inside the remote desktop transport, MTU handling, fragmentation
- Virtual LAN emulation — Layer 2 bridging, ARP proxy, DHCP over tunnel
- Site-to-site connectivity — connecting entire networks through remote desktop peers
- Split tunneling — routing specific traffic through VPN vs. direct, route table management
- Network namespace integration — Linux netns, Windows compartment isolation
- DNS resolution over tunnel — DNS proxy, split DNS, remote DNS forwarding
- Traffic shaping — bandwidth allocation per tunnel, QoS marking, priority queuing
**Extract**: TUN/TAP device creation code, packet encapsulation/delivery logic, routing table manipulation, DNS proxy implementation
**Intrinsic value indicators**: Zero-overhead kernel-bypass tunneling, userspace networking stack with fine-grained routing, platform-agnostic TUN abstraction

### 17. Mesh Networking & Multi-Hop Routing

**Generic category**: Coordination
**Types**: Full mesh, partial mesh, hierarchical mesh, relay mesh, gossip-based discovery
**Look for**:

- Mesh topology management — peer graph maintenance, neighbor discovery, topology reconfiguration
- Multi-hop routing — distance-vector, link-state, source routing. How do packets traverse multiple hops?
- Relay mesh — peers acting as relays for other peers, relay selection criteria, relay rotation
- Gossip protocols — membership dissemination, state propagation, anti-entropy mechanisms
- Route optimization — latency-based path selection, bandwidth-aware routing, congestion-aware path switching
- NAT-to-NAT relay chains — cascading relays when no direct path exists between two peers
- Partition healing — detecting network partitions, automatic reconnection, state reconciliation after merge
- Mesh authentication — how new peers join the mesh, trust establishment, peer attestation
- Overlay networks — DHT-based routing, virtual addressing, content-addressable routing
**Extract**: Routing table data structures, path selection algorithms, gossip message formats, mesh join/leave protocols, partition detection logic
**Intrinsic value indicators**: Latency-aware adaptive routing with sub-second convergence, zero-trust mesh with automatic attestation, DHT-based peer discovery at scale

### 18. Connection Roaming & Handover

**Generic category**: Autonomy & Scheduling
**Types**: Network roaming (Wi-Fi↔cellular↔Ethernet), IP mobility, multipath connections, seamless handover
**Look for**:

- Network change detection — OS notification of interface changes, IP address change monitoring, gateway change detection
- Seamless handover — connection migration without session reset, zero-packet-loss transition strategies
- Multipath transport — MPTCP, QUIC connection migration, SCTP multi-homing. Sending over multiple paths simultaneously
- Connection migration protocol — signaling address changes to the peer, re-establishing encryption after migration
- Roaming state preservation — maintaining session state across network transitions, buffer management during handover
- Split-brain prevention — detecting and resolving duplicate connections after roaming
- Latency spike mitigation — temporary quality reduction during transition, frame buffering strategy
- Mobile-optimized keepalive — adaptive ping intervals based on network type, battery-aware keepalive
**Extract**: Network change detection implementations, connection migration state machines, multipath scheduling algorithms, roaming handoff protocol message formats
**Intrinsic value indicators**: Zero-downtime network roaming with sub-50ms handover, multipath with automatic path quality scoring, predictive handover based on signal strength

### 19. Protocol Interop & Gateway

**Generic category**: Integration & Extension
**Types**: SSH tunneling, RDP/VNC gateway, protocol translation, legacy protocol bridges
**Look for**:

- SSH integration — SSH tunneling as transport, SSH key-based authentication, SSH port forwarding for relay access
- RDP protocol support — RDP client/server implementation, RDP bitmap codec, RDP virtual channel extensions
- VNC protocol support — RFB protocol implementation, Zlib/TightZRLE encoding, VNC security types
- Protocol translation — RDP-to-custom, VNC-to-custom, protocol feature mapping tables
- Gateway/broker pattern — single entry point that routes to multiple backends by protocol, connection multiplexing
- Legacy device support — older RDP versions (5.x, 7.x), VNC 3.3/3.7/3.8, compatibility mode negotiation
- Virtual channel multiplexing — running multiple protocols over a single connection (RDP virtual channels, SSH multiplexing)
- SPICE protocol — QXL driver, SPICE agent, migration support
**Extract**: Protocol handshake implementations, codec feature mapping tables, virtual channel registration code, gateway routing logic
**Intrinsic value indicators**: Zero-copy protocol translation between RDP and custom protocol, unified gateway supporting 4+ protocols, adaptive protocol selection based on network conditions

### 20. Viewer UI & Interaction

**Generic category**: Perception & Input
**Types**: Desktop viewer UI, web viewer UI, mobile viewer UI, toolbar/controls, connection management interface, accessibility
**Look for**:

- Viewer chrome design — toolbar placement, fullscreen toggle, scaling modes (fit/actual/stretch), connection status indicators
- Multi-session UI — tabbed sessions, session sidebar, thumbnail previews, session switching
- Connection management — connection dialog, address book UI, recent connections, QR code sharing
- Touch/gesture controls — pinch-to-zoom, two-finger scroll, long-press right-click, gesture customization
- Accessibility — screen reader support, keyboard navigation, high contrast mode, font scaling
- Settings panels — quality slider, display selection, input mode toggle, keyboard mapping configuration
- File transfer UI — drag-and-drop zones, progress indicators, file browser panel
- Chat/messaging — in-session text chat, system message overlay, notification banners
- Platform-native UI — SwiftUI (macOS), WinUI (Windows), GTK (Linux), Qt, Electron. Web-based (React, Vue)
- Responsive design — window resize handling, dynamic scaling, multi-monitor viewer layout
**Extract**: UI component hierarchies, scaling/viewport calculation code, gesture handler implementations, settings schema definitions
**Intrinsic value indicators**: Zero-latency local cursor with remote cursor overlay, adaptive UI that works across desktop/tablet/mobile, accessible remote desktop with full keyboard navigation

## Category-to-Pillar Mapping

| Generic Category | Pillar(s) |
|-----------------|-----------|
| 1. Data & Storage | 14. File Transfer |
| 2. Processing & Logic | 2. Video Encoding, 3. Video Decoding & Rendering |
| 3. Coordination | 7. P2P Connectivity & NAT Traversal, 12. Session Management, 17. Mesh Networking & Multi-Hop Routing |
| 4. Perception & Input | 1. Screen Capture, 4. Remote Input, 5. Clipboard Sync, 6. Audio Forwarding, 20. Viewer UI & Interaction |
| 5. Goal & Planning | 7. P2P Connectivity & NAT Traversal (connection strategy), 12. Session Management (lifecycle planning) |
| 6. Autonomy & Scheduling | 13. Adaptive Streaming, 18. Connection Roaming & Handover |
| 7. Knowledge & Representation | 11. Peer Identity & Discovery |
| 8. Adaptation & Learning | 13. Adaptive Streaming (quality adaptation) |
| 9. Integration & Extension | 8. Relay Infrastructure, 15. Cross-Platform Build & Deployment, 16. VPN & Virtual Networking, 19. Protocol Interop & Gateway |
| 10. Governance & Quality | 9. Encryption & Key Exchange, 10. Authentication & Authorization |

## Common Gaps in Remote Desktop Systems

Typical architectural gaps found in remote desktop projects:

- No clipboard sync between host and viewer
- No auto-reconnect or session resumption after disconnection
- No concurrent viewer support (single viewer per agent)
- No adaptive bitrate/quality based on network conditions
- No hardware-accelerated video encoding (CPU-only software encoding)
- No hardware-accelerated video decoding
- No audio forwarding
- No file transfer capability
- No multi-display support or dynamic display change handling
- No P2P connectivity (relay-only architecture with single point of failure)
- No NAT traversal (LAN-only or requires manual port forwarding)
- No end-to-end encryption (cleartext or TLS-terminated at relay)
- No proper authentication beyond a shared password
- No input sanitization or rate limiting on remote input
- No proper cross-platform abstraction (platform code scattered throughout)
- No proper build/tag system for platform-conditional compilation
- No browser-based viewer option
- No session management state machine (ad-hoc connection handling)
- No delta/dirty-rect capture optimization
- No encryption key rotation during long sessions
- No address book or persistent peer management
- No VPN/virtual networking mode (cannot tunnel arbitrary IP traffic)
- No mesh topology — all connections are point-to-point or through a single relay
- No connection roaming — session drops on Wi-Fi/cellular/network transitions
- No protocol interop — no SSH tunneling, RDP, or VNC gateway support
- No viewer UI beyond a bare canvas — no toolbar, settings panel, connection manager, or accessibility
- No multi-session viewer (one session per window, no tabbed or sidebar interface)
