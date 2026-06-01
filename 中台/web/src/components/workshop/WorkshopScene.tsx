import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { STATUS_COLORS, STATUS_LABELS, type SubTaskData } from './types';
import './workshop.css';

// --- SkyOffice sprite constants (32x48 per frame, single-row layout) ---
const FW = 32;
const FH = 48;
const CHARS = ['adam', 'nancy', 'ash', 'lucy'] as const;

// Frame indices: idle(right 0-5, up 6-11, left 12-17, down 18-23), run(24-47 same 6-per-dir), sit(48-51)
const IDLE: Record<string, [number, number]> = { e: [0, 5], n: [6, 11], w: [12, 17], s: [18, 23] };
const RUN: Record<string, [number, number]> = { e: [24, 29], n: [30, 35], w: [36, 41], s: [42, 47] };
const SIT: Record<string, number> = { s: 48, w: 49, e: 50, n: 51 };

type Dir = 'n' | 'w' | 's' | 'e';

// --- Scene ---
const SW = 960;
const SH = 540;
const TILE = 32;
const SPEED = 1.0;
const SCALE = 1.8;

// Walkable area bounds
const MIN_X = 80, MAX_X = 880, MIN_Y = 60, MAX_Y = 510;

// Character collision radius
const CHAR_R = 10;

// --- Collision Rect ---
interface CRect { x: number; y: number; w: number; h: number }

function pointInRect(px: number, py: number, r: CRect): boolean {
  return px + CHAR_R > r.x && px - CHAR_R < r.x + r.w &&
    py + CHAR_R > r.y && py - CHAR_R < r.y + r.h;
}

function pointInAnyRect(px: number, py: number, rects: CRect[]): boolean {
  return rects.some(r => pointInRect(px, py, r));
}

function pushOutRects(px: number, py: number, rects: CRect[]): { x: number; y: number } {
  let x = px, y = py;
  for (const r of rects) {
    if (pointInRect(x, y, r)) {
      const dL = x - r.x, dR = r.x + r.w - x, dT = y - r.y, dB = r.y + r.h - y;
      const min = Math.min(dL, dR, dT, dB);
      if (min === dL) x = r.x - CHAR_R - 1;
      else if (min === dR) x = r.x + r.w + CHAR_R + 1;
      else if (min === dT) y = r.y - CHAR_R - 1;
      else y = r.y + r.h + CHAR_R + 1;
    }
  }
  return { x, y };
}

// --- Furniture layout ---
// Desk sprite in Modern_Office tileset: cols 0-2, rows 0-3 = 96x128
// Computer sprite from computer.png: 32x64 per frame
// Chair sprite from chair.png: 32x32 per frame
const FURN_S = 0.75; // furniture scale
const DK_W = 96 * FURN_S;  // 72
const DK_H = 128 * FURN_S; // 96
const MON_W = 32 * 0.55;   // ~18
const MON_H = 64 * 0.55;   // ~35
const CH_W = 32 * FURN_S;  // 24
const CH_H = 32 * FURN_S;  // 24

interface WorkstationDef { x: number; y: number }
interface MeetingDef { x: number; y: number; w: number; h: number }
interface SofaDef { x: number; y: number }

const WORKSTATIONS: WorkstationDef[] = [
  { x: 50, y: 60 },
  { x: 250, y: 60 },
  { x: 460, y: 60 },
  { x: 680, y: 60 },
];

const MEETING_TABLE: MeetingDef = { x: 340, y: 260, w: 240, h: 80 };

const SOFAS: SofaDef[] = [
  { x: 55, y: 420 },
  { x: 680, y: 420 },
];

const COFFEE_TABLE = { x: 400, y: 435, w: 80, h: 40 };

// Build collision rects from furniture layout
function buildCollisionRects(): CRect[] {
  const rects: CRect[] = [];
  for (const ws of WORKSTATIONS) {
    // Desk + chair area (slightly padded)
    rects.push({ x: ws.x - 4, y: ws.y, w: DK_W + 8, h: DK_H + CH_H + 8 });
  }
  // Meeting table + chairs
  rects.push({ x: MEETING_TABLE.x - 10, y: MEETING_TABLE.y - CH_H - 4, w: MEETING_TABLE.w + 20, h: MEETING_TABLE.h + CH_H * 2 + 8 });
  // Sofas
  for (const s of SOFAS) {
    rects.push({ x: s.x - 4, y: s.y - 4, w: 192, h: 80 });
  }
  // Coffee table
  rects.push({ x: COFFEE_TABLE.x - 4, y: COFFEE_TABLE.y - 4, w: COFFEE_TABLE.w + 8, h: COFFEE_TABLE.h + 8 });
  return rects;
}

const COLLISION_RECTS = buildCollisionRects();

interface CharState {
  name: string;
  ci: number;
  x: number; y: number;
  tx: number; ty: number;
  status: string;
  task: string;
  dir: Dir;
  moving: boolean;
  frame: number;
  tick: number;
}

interface Member { name: string; status: string; task: string }

interface Props {
  projectName: string;
  subTasks: SubTaskData[];
  selectedMember?: string | null;
  onMemberSelect?: (name: string | null) => void;
}

function rand(a: number, b: number) { return a + Math.random() * (b - a); }

function randomWalkable(rects: CRect[]): { x: number; y: number } {
  let x: number, y: number, tries = 0;
  do {
    x = rand(MIN_X, MAX_X);
    y = rand(MIN_Y, MAX_Y);
    tries++;
  } while (pointInAnyRect(x, y, rects) && tries < 50);
  return { x, y };
}

function extractMembers(subTasks: SubTaskData[]): Member[] {
  const m = new Map<string, Member>();
  const p = ['active', 'dispatched', 'rework', 'blocked', 'pending', 'completed'];
  for (const st of subTasks) {
    let names: string[] = [];
    try { names = JSON.parse(st.assignees || '[]'); } catch { /* */ }
    for (const n of names) {
      if (!n) continue;
      const ex = m.get(n);
      if (!ex || p.indexOf(st.status) < p.indexOf(ex.status))
        m.set(n, { name: n, status: st.status, task: st.title });
    }
  }
  return Array.from(m.values());
}

function dxDir(dx: number): Dir {
  if (Math.abs(dx) < 0.3) return 's';
  return dx > 0 ? 'e' : 'w';
}

// --- Member Panel ---
const Panel: React.FC<{ members: Member[]; sel: string | null; onSel: (n: string | null) => void }> = ({ members, sel, onSel }) => (
  <div className="ws-member-panel">
    <div style={{ padding: '12px 12px 8px', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
        <span style={{ color: 'rgba(255,255,255,0.7)', fontSize: 13, fontWeight: 600 }}>成员</span>
        {sel && <span onClick={() => onSel(null)} style={{ color: '#1890ff', fontSize: 11, cursor: 'pointer' }}>全部</span>}
      </div>
      <div style={{ color: 'rgba(255,255,255,0.35)', fontSize: 11 }}>{members.length} 人</div>
    </div>
    {members.map(m => {
      const s = sel === m.name, d = sel !== null && !s, c = STATUS_COLORS[m.status] || '#555';
      return (
        <div key={m.name} className={`ws-member-item${s ? ' selected' : ''}${d ? ' dimmed' : ''}`}
          onClick={() => onSel(s ? null : m.name)}>
          <div className="ws-member-avatar" style={{ background: c }}>{m.name.charAt(0)}</div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ color: '#eee', fontSize: 12, fontWeight: 500 }}>{m.name}</div>
            <div style={{ color: 'rgba(255,255,255,0.4)', fontSize: 10, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{m.task}</div>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 2 }}>
            <div style={{ width: 8, height: 8, borderRadius: '50%', background: c, flexShrink: 0 }} />
            <span style={{ color: 'rgba(255,255,255,0.3)', fontSize: 8 }}>{STATUS_LABELS[m.status]}</span>
          </div>
        </div>
      );
    })}
  </div>
);

// --- Main ---
const WorkshopScene: React.FC<Props> = ({ projectName, subTasks, selectedMember, onMemberSelect }) => {
  const members = useMemo(() => extractMembers(subTasks), [subTasks]);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const charsRef = useRef<CharState[]>([]);
  const [_, setTick] = useState(0);
  const rafRef = useRef(0);
  const lastSync = useRef(0);
  const timers = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());

  // Sprite caches
  const imgs = useRef<Record<string, HTMLImageElement>>({});
  const loaded = useRef(false);
  const tileImgs = useRef<Record<string, HTMLImageElement>>({});

  // Preload all sprites
  useEffect(() => {
    let count = 0;
    const total = CHARS.length + 4; // chars + floor + office tileset + computer + chair
    const done = () => { count++; if (count >= total) loaded.current = true; };

    CHARS.forEach(name => {
      const img = new Image();
      img.src = `/assets/characters/${name}.png`;
      img.onload = () => { imgs.current[name] = img; done(); };
      img.onerror = done;
    });

    const tilesets = ['FloorAndGround', 'Modern_Office_Black_Shadow'];
    const extras = [
      { key: 'computer', path: '/assets/tilesets/computer.png' },
      { key: 'chair', path: '/assets/tilesets/chair.png' },
    ];

    tilesets.forEach(name => {
      const img = new Image();
      img.src = `/assets/tilesets/${name}.png`;
      img.onload = () => { tileImgs.current[name] = img; done(); };
      img.onerror = done;
    });

    extras.forEach(({ key, path }) => {
      const img = new Image();
      img.src = path;
      img.onload = () => { tileImgs.current[key] = img; done(); };
      img.onerror = done;
    });
  }, []);

  // Init characters
  useEffect(() => {
    const prev = charsRef.current;
    const updated: CharState[] = [];
    for (let i = 0; i < members.length; i++) {
      const m = members[i];
      const ex = prev.find(c => c.name === m.name);
      if (ex) {
        updated.push({ ...ex, status: m.status, task: m.task });
      } else {
        const pos = randomWalkable(COLLISION_RECTS);
        const target = randomWalkable(COLLISION_RECTS);
        updated.push({ name: m.name, ci: i % 4, x: pos.x, y: pos.y, tx: target.x, ty: target.y, status: m.status, task: m.task, dir: 's', moving: true, frame: 0, tick: 0 });
      }
    }
    charsRef.current = updated;
    setTick(t => t + 1);
  }, [members]);

  // Target scheduling with collision-aware targets
  useEffect(() => {
    timers.current.forEach(t => clearTimeout(t));
    timers.current.clear();
    const sched = (name: string, immediate = false) => {
      const delay = immediate ? 0 : (2500 + Math.random() * 3000);
      const t = setTimeout(() => {
        const ch = charsRef.current.find(c => c.name === name);
        if (ch) {
          const pos = randomWalkable(COLLISION_RECTS);
          ch.tx = pos.x;
          ch.ty = pos.y;
        }
        sched(name);
      }, delay);
      timers.current.set(name, t);
    };
    for (const ch of charsRef.current) sched(ch.name, true);
    return () => { timers.current.forEach(t => clearTimeout(t)); timers.current.clear(); };
  }, [members]);

  // --- Render ---
  const render = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas || !loaded.current) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = SW * dpr;
    canvas.height = SH * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.imageSmoothingEnabled = false;

    const floor = tileImgs.current['FloorAndGround'];
    const office = tileImgs.current['Modern_Office_Black_Shadow'];
    const compImg = tileImgs.current['computer'];
    const chairImg = tileImgs.current['chair'];

    // === FLOOR ===
    ctx.fillStyle = '#1a1a2a';
    ctx.fillRect(0, 0, SW, SH);

    if (floor && floor.complete) {
      const fx = 27 * TILE, fy = 6 * TILE;
      for (let ty = 0; ty < SH; ty += TILE)
        for (let tx = 0; tx < SW; tx += TILE)
          ctx.drawImage(floor, fx, fy, TILE, TILE, tx, ty, TILE, TILE);

      // Dark border
      const bx = 6 * TILE, by = 25 * TILE;
      for (let tx = 0; tx < SW; tx += TILE) {
        ctx.drawImage(floor, bx, by, TILE, TILE, tx, 0, TILE, TILE);
        ctx.drawImage(floor, bx, by, TILE, TILE, tx, TILE, TILE, TILE);
        ctx.drawImage(floor, bx, by, TILE, TILE, tx, SH - TILE, TILE, TILE);
      }
      for (let ty = TILE * 2; ty < SH - TILE; ty += TILE) {
        ctx.drawImage(floor, bx, by, TILE, TILE, 0, ty, TILE, TILE);
        ctx.drawImage(floor, bx, by, TILE, TILE, SW - TILE, ty, TILE, TILE);
      }
    }

    // === HEADER ===
    ctx.fillStyle = 'rgba(0,0,0,0.4)';
    ctx.fillRect(0, 0, SW, 36);
    ctx.fillStyle = 'rgba(255,255,255,0.7)';
    ctx.font = '600 13px sans-serif';
    ctx.fillText(`工作坊: ${projectName}`, 16, 24);
    ctx.fillStyle = 'rgba(255,255,255,0.4)';
    ctx.font = '11px sans-serif';
    ctx.textAlign = 'end';
    ctx.fillText(`${members.length} 人在线`, SW - 16, 24);
    ctx.textAlign = 'start';

    // === FURNITURE RENDERING (sorted by Y for depth) ===
    // We need to interleave furniture and characters by Y position

    // Collect all renderables
    type Renderable = {
      y: number; // sort key (feet Y / bottom Y)
      draw: () => void;
    };

    const renderables: Renderable[] = [];

    // -- Workstations (need office tileset) --
    if (office && office.complete) {
      for (const ws of WORKSTATIONS) {
        const deskBottomY = ws.y + DK_H;
        const chairBottomY = ws.y + DK_H + 8 + CH_H;

        renderables.push({
          y: ws.y + DK_H * 0.5,
          draw: () => {
            // Complete desk: cols 0-2, rows 0-3 of Modern_Office (96x128)
            ctx.drawImage(office, 0, 0, 96, 128, ws.x, ws.y, DK_W, DK_H);

            // Monitor on desk surface (centered, near back)
            if (compImg && compImg.complete) {
              const monX = ws.x + DK_W / 2 - MON_W / 2;
              const monY = ws.y + 12;
              ctx.drawImage(compImg, 0, 0, 32, 64, monX, monY, MON_W, MON_H);
            }

            // Keyboard on desk surface
            ctx.drawImage(office, 13 * TILE, 12 * TILE, TILE, TILE, ws.x + DK_W / 2 - TILE * FURN_S / 2, ws.y + DK_H * 0.45, TILE * FURN_S, TILE * FURN_S);
          },
        });

        // Chair in front of desk
        renderables.push({
          y: chairBottomY,
          draw: () => {
            if (chairImg && chairImg.complete) {
              const chX = ws.x + DK_W / 2 - CH_W / 2;
              const chY = ws.y + DK_H + 4;
              ctx.drawImage(chairImg, 0, 0, 32, 32, chX, chY, CH_W, CH_H);
            }
          },
        });
      }

      // -- Decorative Plants --
      renderables.push({
        y: 50,
        draw: () => {
          const ps = FURN_S * 1.2;
          ctx.drawImage(office, 6 * TILE, 8 * TILE, TILE, 2 * TILE, 38, 42, TILE * ps, 2 * TILE * ps);
          ctx.drawImage(office, 6 * TILE, 8 * TILE, TILE, 2 * TILE, SW - 38 - TILE * ps, 42, TILE * ps, 2 * TILE * ps);
          ctx.drawImage(office, 6 * TILE, 12 * TILE, TILE, TILE, 38, SOFAS[0].y - TILE * FURN_S - 4, TILE * FURN_S, TILE * FURN_S);
          ctx.drawImage(office, 6 * TILE, 12 * TILE, TILE, TILE, SW - 38 - TILE * FURN_S, SOFAS[1].y - TILE * FURN_S - 4, TILE * FURN_S, TILE * FURN_S);
        },
      });

      // -- Bookshelf (left wall) --
      renderables.push({
        y: 200,
        draw: () => {
          ctx.drawImage(office, 0, 28 * TILE, TILE, 4 * TILE, 4, 150, TILE * FURN_S, 4 * TILE * FURN_S);
        },
      });

      // -- Filing Cabinet (right wall) --
      renderables.push({
        y: 280,
        draw: () => {
          ctx.drawImage(office, 0, 40 * TILE, TILE, 3 * TILE, SW - TILE * FURN_S - 4, 200, TILE * FURN_S, 3 * TILE * FURN_S);
        },
      });
    }

    // -- Canvas-drawn furniture (no tileset dependency) --

    // Meeting Table
    renderables.push({
      y: MEETING_TABLE.y + MEETING_TABLE.h,
      draw: () => {
        const mtX = MEETING_TABLE.x;
        const mtY = MEETING_TABLE.y;
        const mw = MEETING_TABLE.w;
        const mh = MEETING_TABLE.h;

        // Table top surface (dark wood)
        ctx.fillStyle = '#6b4c2a';
        ctx.fillRect(mtX, mtY, mw, mh * 0.5);
        ctx.fillStyle = '#8b6c4a';
        ctx.fillRect(mtX, mtY, mw, 4);
        ctx.fillRect(mtX, mtY, 4, mh * 0.5);
        ctx.fillStyle = '#4a2c0a';
        ctx.fillRect(mtX + mw - 4, mtY, 4, mh * 0.5);
        ctx.fillRect(mtX, mtY + mh * 0.5 - 3, mw, 3);

        // Table front panel
        ctx.fillStyle = '#5a3c1a';
        ctx.fillRect(mtX, mtY + mh * 0.5, mw, mh * 0.5);
        ctx.fillStyle = '#7a5c3a';
        ctx.fillRect(mtX, mtY + mh * 0.5, mw, 3);
        ctx.fillStyle = '#3a1c00';
        ctx.fillRect(mtX + mw - 3, mtY + mh * 0.5, 3, mh * 0.5);
        ctx.fillRect(mtX, mtY + mh - 3, mw, 3);

        // Table legs
        ctx.fillStyle = '#4a2c0a';
        ctx.fillRect(mtX + 6, mtY + mh, 6, 8);
        ctx.fillRect(mtX + mw - 12, mtY + mh, 6, 8);

        // Chairs around table
        if (chairImg && chairImg.complete) {
          const chairs = [
            { x: mtX + mw * 0.2 - CH_W / 2, y: mtY - CH_H - 4 },
            { x: mtX + mw * 0.5 - CH_W / 2, y: mtY - CH_H - 4 },
            { x: mtX + mw * 0.8 - CH_W / 2, y: mtY - CH_H - 4 },
            { x: mtX + mw * 0.2 - CH_W / 2, y: mtY + mh + 8 },
            { x: mtX + mw * 0.5 - CH_W / 2, y: mtY + mh + 8 },
            { x: mtX + mw * 0.8 - CH_W / 2, y: mtY + mh + 8 },
          ];
          for (const c of chairs) {
            ctx.drawImage(chairImg, 0, 0, 32, 32, c.x, c.y, CH_W, CH_H);
          }
        }
      },
    });

    // Sofas
    const drawSofa = (sx: number, sy: number, sw: number, sh: number, color: string) => {
      const darker = 'rgba(0,0,0,0.2)';
      // Backrest
      ctx.fillStyle = color;
      ctx.fillRect(sx, sy, sw, sh * 0.35);
      ctx.fillStyle = darker;
      ctx.fillRect(sx, sy, sw, 4);
      // Seat cushion (lighter)
      const seatColor = color === '#3a4a6a' ? '#4a5a7a' : '#5a6a5a';
      ctx.fillStyle = seatColor;
      ctx.fillRect(sx + 8, sy + sh * 0.35, sw - 16, sh * 0.45);
      // Cushion divider
      ctx.fillStyle = 'rgba(0,0,0,0.15)';
      ctx.fillRect(sx + sw / 2 - 1, sy + sh * 0.35, 2, sh * 0.45);
      // Front edge shadow
      ctx.fillStyle = 'rgba(0,0,0,0.25)';
      ctx.fillRect(sx + 8, sy + sh * 0.8 - 2, sw - 16, 2);
      // Armrests
      ctx.fillStyle = color;
      ctx.fillRect(sx, sy + sh * 0.25, 10, sh * 0.6);
      ctx.fillRect(sx + sw - 10, sy + sh * 0.25, 10, sh * 0.6);
      ctx.fillStyle = darker;
      ctx.fillRect(sx + 8, sy + sh * 0.25, 2, sh * 0.6);
      ctx.fillRect(sx + sw - 10, sy + sh * 0.25, 2, sh * 0.6);
      // Legs
      ctx.fillStyle = '#2a1a0a';
      ctx.fillRect(sx + 4, sy + sh - 4, 5, 4);
      ctx.fillRect(sx + sw - 9, sy + sh - 4, 5, 4);
    };

    for (const sofa of SOFAS) {
      renderables.push({
        y: sofa.y + 80,
        draw: () => {
          drawSofa(sofa.x, sofa.y, 192, 80, '#3a4a6a');
        },
      });
    }

    // Coffee Table
    renderables.push({
      y: COFFEE_TABLE.y + COFFEE_TABLE.h,
      draw: () => {
        const cx = COFFEE_TABLE.x, cy = COFFEE_TABLE.y;
        const cw = COFFEE_TABLE.w, ch = COFFEE_TABLE.h;
        ctx.fillStyle = '#7a5c3a';
        ctx.fillRect(cx, cy, cw, ch * 0.5);
        ctx.fillStyle = '#8b6c4a';
        ctx.fillRect(cx, cy, cw, 3);
        ctx.fillStyle = '#5a3c1a';
        ctx.fillRect(cx, cy + ch * 0.5, cw, ch * 0.5);
        ctx.fillStyle = '#3a1c00';
        ctx.fillRect(cx + 4, cy + ch, 4, 6);
        ctx.fillRect(cx + cw - 8, cy + ch, 4, 6);
      },
    });

    // -- Characters as renderables --
    for (const ch of charsRef.current) {
      renderables.push({
        y: ch.y,
        draw: () => {
          const isSel = selectedMember === ch.name;
          const isDim = selectedMember != null && !isSel;
          ctx.globalAlpha = isDim ? 0.2 : 1;

          const img = imgs.current[CHARS[ch.ci]];
          if (!img || !img.complete) { ctx.globalAlpha = 1; return; }

          const [lo, hi] = ch.moving ? RUN[ch.dir] : IDLE[ch.dir];
          const frameIdx = lo + ch.frame;
          const sx = frameIdx * FW;
          const dw = FW * SCALE, dh = FH * SCALE;
          const dx = ch.x - dw / 2, dy = ch.y - dh;

          // Selection glow
          if (isSel) {
            ctx.strokeStyle = 'rgba(24,144,255,0.7)';
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.ellipse(ch.x, ch.y + 2, 18, 5, 0, 0, Math.PI * 2);
            ctx.stroke();
          }

          // Shadow
          ctx.fillStyle = 'rgba(0,0,0,0.18)';
          ctx.beginPath();
          ctx.ellipse(ch.x, ch.y + 2, 14, 4, 0, 0, Math.PI * 2);
          ctx.fill();

          // Sprite
          ctx.imageSmoothingEnabled = false;
          ctx.drawImage(img, sx, 0, FW, FH, dx, dy, dw, dh);

          // Name tag
          ctx.font = '600 10px sans-serif';
          const nw = ctx.measureText(ch.name).width;
          ctx.fillStyle = 'rgba(0,0,0,0.55)';
          ctx.beginPath();
          ctx.roundRect(ch.x - nw / 2 - 4, ch.y + 6, nw + 8, 15, 3);
          ctx.fill();
          ctx.fillStyle = '#eee';
          ctx.textAlign = 'center';
          ctx.fillText(ch.name, ch.x, ch.y + 17);
          ctx.textAlign = 'start';

          // Status bubble
          const sc = STATUS_COLORS[ch.status] || '#555';
          const sl = STATUS_LABELS[ch.status] || '';
          const bw = ctx.measureText(sl).width + 10;
          const by = dy - 6;
          ctx.fillStyle = sc;
          ctx.globalAlpha = isDim ? 0.2 : 0.9;
          ctx.beginPath();
          ctx.roundRect(ch.x - bw / 2, by - 13, bw, 15, 4);
          ctx.fill();
          ctx.fillStyle = '#fff';
          ctx.font = 'bold 8px sans-serif';
          ctx.textAlign = 'center';
          ctx.fillText(sl, ch.x, by - 2);
          ctx.textAlign = 'start';
          ctx.globalAlpha = 1;
        },
      });
    }

    // Sort all renderables by Y and draw
    renderables.sort((a, b) => a.y - b.y);
    for (const r of renderables) r.draw();
  }, [selectedMember, members, projectName]);

  // --- Animation loop ---
  useEffect(() => {
    const animate = (ts: number) => {
      for (const ch of charsRef.current) {
        const dx = ch.tx - ch.x, dy = ch.ty - ch.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist > 4) {
          let nx = ch.x + (dx / dist) * Math.min(SPEED, dist);
          let ny = ch.y + (dy / dist) * Math.min(SPEED, dist);

          // Collision resolution
          const resolved = pushOutRects(nx, ny, COLLISION_RECTS);
          nx = resolved.x;
          ny = resolved.y;

          // Clamp to walkable area
          nx = Math.max(MIN_X, Math.min(MAX_X, nx));
          ny = Math.max(MIN_Y, Math.min(MAX_Y, ny));

          ch.x = nx;
          ch.y = ny;
          ch.dir = dxDir(dx);
          ch.moving = true;
          ch.tick++;
          if (ch.tick >= 5) { ch.tick = 0; ch.frame = (ch.frame + 1) % 6; }
        } else if (ch.moving) {
          ch.moving = false; ch.frame = 0; ch.tick = 0;
        } else {
          ch.tick++;
          if (ch.tick >= 20) { ch.tick = 0; ch.frame = (ch.frame + 1) % 6; }
        }
      }
      if (ts - lastSync.current > 60) { lastSync.current = ts; render(); }
      rafRef.current = requestAnimationFrame(animate);
    };
    rafRef.current = requestAnimationFrame(animate);
    return () => { if (rafRef.current) cancelAnimationFrame(rafRef.current); };
  }, [render]);

  const handleClick = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const sx = SW / rect.width, sy = SH / rect.height;
    const mx = (e.clientX - rect.left) * sx, my = (e.clientY - rect.top) * sy;
    const sorted = [...charsRef.current].sort((a, b) => b.y - a.y);
    for (const ch of sorted) {
      if (Math.abs(mx - ch.x) < 25 && Math.abs(my - ch.y + FH * SCALE / 2) < 35) {
        onMemberSelect?.(selectedMember === ch.name ? null : ch.name);
        return;
      }
    }
    onMemberSelect?.(null);
  }, [selectedMember, onMemberSelect]);

  return (
    <div className="ws-scene">
      <canvas ref={canvasRef}
        style={{ width: SW, height: SH, flex: 1, maxWidth: SW, cursor: 'pointer', borderRadius: '12px 0 0 12px' }}
        onClick={handleClick} />
      <Panel members={members} sel={selectedMember || null} onSel={n => onMemberSelect?.(n)} />
    </div>
  );
};

export default WorkshopScene;
