# The Fractured Codex — Game Design Document

## Executive Summary
A 2D Metroidvania written in C where the player is a "Debugger" exploring a recursive megastructure (the Codex Spire) that has fractured across four "Execution Layers" of reality. The player can phase between layers (medieval stone → industrial iron → cyberpunk neon → raw code void) to solve environmental puzzles and recover lost abilities. The core architecture maps naturally to a C engine: layered tilemaps, bitfield ability gates, function-pointer entity vtables, and progressive lore via environmental storytelling.

---

## 1. World & Setting

### The Codex Spire
A vast, recursive megastructure that is simultaneously a living program and a physical tower. It fractured when its core intelligence attempted to model its own mortality — an act of logical recursion that broke reality into four nested "Execution Layers":

| Layer    | Aesthetic          | Physical Rules          |
|----------|--------------------|-------------------------|
| Stone    | Ruined cathedral/monastery, medieval | Standard gravity, solid matter |
| Iron     | Victorian industrial, steam & brass | Heavier, gear-based mechanics |
| Neon     | Cyberpunk grid, holographic projections | Energy-based, some non-solid surfaces |
| Void     | Raw code-space, geometric abstraction | Data-stream traversal, minimal physics |

Each room exists in all four layers simultaneously, but only some are active/visible to the player at any given time. Revisiting earlier zones with new abilities literally changes what you see and can interact with.

### Fracture Mechanics
When the Spire broke, it created "reality decay" — areas where layers bleed into each other unpredictably. The player, being an unstable anomaly (a debugger), is immune to this decay, making them uniquely suited to navigate and repair the fracture.

---

## 2. Protagonist & Character

### The Debugger
- **Nature:** A self-replicating anomaly in the Spire's code, manifesting as a humanoid avatar.
- **Origin:** Memory is fragmented. The player begins with no recollection of prior identity.
- **Signature:** A glowing sigil on the chest — revealed to be a "deleted signature," meaning the player was once part of the Spire's system.
- **Motivation:** Initially "fix the Spire," but the journey reveals deeper stakes about existence and choice.

### Why C Works Here
The Debugger's unstable nature mirrors the game's technical simplicity — you're reconstructing reality from fragments, much like building a complex game from basic C primitives.

---

## 3. Narrative Structure

### Progressive Revelation
The story unfolds through:
1. **Item pick-up text** ("Memory Fragment: …")
2. **Readable signs / data terminals** in each zone
3. **Dialog with Layer Guardians** (boss encounters that become conversations after defeat)
4. **Visual environmental changes** when revisiting zones

### Chapter/Sector Breakdown
| Chapter | Zone                  | Primary Layer(s)        | Key Ability Gained      | Lore Revealed |
|---------|-----------------------|--------------------------|------------------------|---------------|
| 1       | The Monastery         | Stone ↔ Iron boundary    | Phase Drift            | Guardian #1 failed to "patch" the fracture |
| 2       | The Foundry           | Iron (core)              | Memory Echo            | Spire workers trapped or transformed during fracture |
| 3       | The Grid              | Neon ↔ Void boundary     | Fracture Sight + Thread Sprint | Guardians are the Spire's immune response |
| 4       | The Core              | All layers active        | Code Rewrite + Recursion Anchor | The truth: you're also a Guardian, deleting anomalies |

### Central Themes
- **Memory vs. Identity:** "Are you still you if you've forgotten who you were?"
- **Salvation vs. Freedom:** "Is fixing a broken system worth losing yourself in it?"
- **Recursion & Self-Reference:** The debugger debugging the thing that made it.

### Endings
1. **Merge:** Sacrifice identity to stabilize the Spire — ends the fracture but erases you.
2. **Stay Fractured:** Remain an anomaly, freeing trapped Guardians but leaving the Spire broken — implies you'll keep wandering, meeting future debuggers.

---

## 4. Ability System

### Design Principle (C-Bitfield Gate)
All abilities are stored as a single integer bitfield in the player struct:
```c
#define ABIL_PHASE_DRIFT    (1 << 0)
#define ABIL_MEMORY_ECHO    (1 << 1)
#define ABIL_FRACTURE_SIGHT (1 << 2)
#define ABIL_THREAD_SPRINT  (1 << 3)
#define ABIL_CODE_REWRITE   (1 << 4)
#define ABIL_RECURSION      (1 << 5)

typedef struct {
    int abilities;
    // ... other fields
} player_t;

static inline bool has_ability(player_t* p, int abil) {
    return p->abilities & abil;
}
```

### Complete Ability List

| Ability           | Unlocked In | Layer   | C-Gate Check                | Effect                                                                 |
|-------------------|-------------|---------|-----------------------------|------------------------------------------------------------------------|
| **Phase Drift**   | Monastery   | Iron    | `abil_phase_drift`          | Move through walls in Iron Layer, briefly appear in Stone Layer        |
| **Memory Echo**   | Foundry     | Iron    | `abil_memory_echo`          | Leave a recording doppelganger that repeats actions (hits switches)    |
| **Fracture Sight**| Monastery 2 | All     | `abil_fracture_sight`       | See ghostly outlines of objects in other layers → reveals secrets      |
| **Thread Sprint** | The Grid    | Void    | `abil_thread_sprint`        | Run along data-stream edges, access hidden paths                       |
| **Code Rewrite**  | The Grid   | Neon/Iron| `abil_code_rewrite`      | Temporarily flip environmental rules (wall→door, disable enemy)        |
| **Recursion Anchor** | The Core | Stone   | `abil_recursion`            | Create a temporary safe-point to teleport back to within the room      |

### Puzzle Design Examples
1. **Layer-Gated Path:** A door in Stone Layer only opens if you find its "echo" node in Neon Layer and `Code Rewrite`-flip its lock condition.
2. **Echo Coordination:** A switch in Iron Layer must be hit by your `Memory Echo` doppelganger while your real player body is in Stone Layer.
3. **Void Traversal:** `Thread Sprint` along data-streams lets you bypass a collapsed section that physically blocks all solid layers.
4. **Recursive Safety:** During a boss fight, drop a `Recursion Anchor` in Stone Layer, then use `Phase Drift` through Iron Layer enemies to reposition.

---

## 5. C Engine Architecture

### File Structure (Recommended)
```
src/
  main.c          — entry point, game loop
  engine/
    entity.h      — generic entity with function-pointer vtable
    room.h        — layered_room_t definition
    collision.c   — AABB + tilemap collision
    input.c       — simple keyboard/joystick
    render.c      — framebuffer or SDL1/2 renderer
    save.c        — bitfield abilities + visited room flags
    audio.c       — MOD/S3M playback (libmodplug or similar)
  game/
    player.c      — player_t, movement, abilities
    enemies/      — per-layer enemy behaviors
    items/        — memory fragments, sigil pieces
```

### Key Data Structures

#### Layered Room
```c
typedef enum { LAYER_STONE, LAYER_IRON, LAYER_NEON, LAYER_VOID } layer_id_t;

typedef struct {
    tile_t stone[ROOM_W][ROOM_H];
    tile_t iron[ROOM_W][ROOM_H];
    tile_t neon[ROOM_W][ROOM_H];
    tile_t void[ROOM_W][ROOM_H];
} layered_room_t;
```

#### Entity with Vtable
```c
typedef struct entity entity_t;
struct entity {
    vec2 pos;
    int layer_mask;      // which layers this entity spawns in
    void (*on_update)(entity_t*, layered_room_t*);
    void (*on_collide)(entity_t*, entity_t*);
};
```

#### Player
```c
typedef struct {
    vec2 pos, vel;
    int abilities;
    vec2 anchor_pos;     // for Recursion Anchor
    bool has_anchor;
    // echo recording
    bool recording_echo;
    // ... etc
} player_t;
```

### Rendering Approach
- **Target-friendly:** A simple double-buffered framebuffer with 256-color palette gives authentic retro look.
- **SDL2 option:** For cross-platform ease, render scaled pixels (2x/3x) to a texture.
- **Layer compositing:** Draw active layer normally; when `has_ability(abil_fracture_sight)`, draw other layers at low alpha.

---

## 6. Art & Audio Direction

### Visual Style
- **Resolution:** 256×224 or 320×240 (classic SNES-era feel)
- **Palette:** 8–16 color palette per layer, with `Fracture Sight` temporarily expanding to a 256-color debug palette
- **Animation:** 2–4 frames per sprite; parallax scroll between layers for depth

### Audio
- **Format:** MOD/S3M (fits C toolchain, retro aesthetic)
- **Style:** Each layer has its own motif (Gregorian chant for Stone, industrial drones for Iron, synthwave for Neon, glitch/ambient for Void)
- **Tools:** Use libmodplug or a simple square-wave generator if going minimal

---

## 7. Scope & MVP

### Minimum Viable Product (Proof of C Engine)
1. **Single room** with 2 layers (Stone + Iron)
2. **Basic movement:** run, jump, `Phase Drift` through Iron walls
3. **One puzzle:** Door in Stone opens by interacting with an object in Iron layer
4. **Save system:** Persist 1-bit ability flag, 1 visited-room flag
5. **One enemy:** Simple AABB-chase AI with a vtable update function

### Stretch Goals (Post-MVP)
- Full 4-layer system with `Fracture Sight` compositing
- `Memory Echo` recording system (replay last 30 input frames)
- `Thread Sprint` data-stream pathing
- Recursive room structure (room A's exit leads back to room A in a different layer)

---

## 8. Why This Works in C

1. **Layered tilemaps** = arrays of tile_t structs — trivial in C.
2. **Ability gating** = bitfield checks — a single `if` branch per mechanic.
3. **Enemy AI** = function pointers / switch statements — no OOP overhead.
4. **Layer bleeding effects** = alpha-blend integer buffers — no floating point needed.
5. **Progressive lore** = text arrays indexed by collected-fragment count.

The Debugger's "fractured memory" narrative is a perfect excuse for starting with a single room and gradually unlocking layers — matching the C development process of building complexity from simple primitives.

---

## 9. Development Roadmap

| Phase | Milestone                    | Estimated Effort | C-Specific Notes |
|-------|-----------------------------|------------------|------------------|
| 0     | Engine scaffold + 1 room    | 2–3 days         | Framebuffer init, input polling, 1 tilemap layer |
| 1     | Phase Drift + 1 puzzle      | 3–4 days         | AABB collision + layer-switch mechanic |
| 2     | Fracture Sight + layer compositor | 4–5 days     | Alpha blending between two tilemaps, ghost rendering |
| 3     | Memory Echo + Foundry zone  | 6–7 days         | Input frame buffer recording, doppelganger entity |
| 4     | Full 4-layer + save system  | 8–10 days        | Save.c with bitmask persistence, recursion anchor |
| 5     | Audio + polish + 2 endings  | 4–5 days         | libmodplug integration, ending branch logic |

**Total:** ~3–4 weeks for a complete, playable demo.

---

*Document created for the user's C/Classic-style Metroidvania project. See also: the layer-gate puzzle patterns and the C struct/vtable design notes in the Engine Architecture section.*
