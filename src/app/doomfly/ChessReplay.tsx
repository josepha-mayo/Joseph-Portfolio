'use client';

import { useEffect, useState } from 'react';

type Move = {
  side: 'connectome' | 'random';
  uci: string;
  san: string;
  fen_before: string;
  fen_after: string;
};

type Game = { moves: Move[]; summary: { result: string; plies: number } };

const glyphs: Record<string, string> = {
  K: '♔', Q: '♕', R: '♖', B: '♗', N: '♘', P: '♙',
  k: '♚', q: '♛', r: '♜', b: '♝', n: '♞', p: '♟',
};
const pieceNames: Record<string, string> = {
  k: 'king', q: 'queen', r: 'rook', b: 'bishop', n: 'knight', p: 'pawn',
};

function squares(fen: string): string[] {
  return fen.split(' ')[0].split('/').flatMap((rank) =>
    [...rank].flatMap((piece) => /[1-8]/.test(piece) ? Array(Number(piece)).fill('') : [piece])
  );
}

export default function ChessReplay() {
  const [game, setGame] = useState<Game | null>(null);
  const [error, setError] = useState(false);
  const [ply, setPly] = useState(0);
  const [playing, setPlaying] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    fetch('/doomfly/chess-game.json', { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error('Unable to load recorded game');
        return response.json();
      })
      .then((record: Game) => setGame(record))
      .catch((err) => { if (err.name !== 'AbortError') setError(true); });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!playing || !game || ply >= game.moves.length) return;
    const timer = window.setTimeout(() => setPly((current) => current + 1), 750);
    return () => window.clearTimeout(timer);
  }, [playing, ply, game]);

  if (error) return <p role="alert" className="p-6 text-text-secondary">The replay could not load. You can still download the PGN below.</p>;
  if (!game) return <div className="aspect-square max-w-lg animate-pulse bg-white/5 rounded-xl" role="status">Loading recorded moves…</div>;

  const move = ply ? game.moves[ply - 1] : null;
  const fen = move ? move.fen_after : game.moves[0].fen_before;
  const lastSquares = move ? [move.uci.slice(0, 2), move.uci.slice(2, 4)] : [];
  const choosePly = (next: number) => { setPlaying(false); setPly(next); };
  const buttonStyle = 'rounded-md border border-border-highlight px-4 py-2 text-sm hover:border-accent hover:text-accent disabled:opacity-30 disabled:cursor-not-allowed transition-colors';

  return (
    <div className="grid lg:grid-cols-[1.15fr_1fr] gap-8 items-start">
      <div>
        <div className="flex justify-between gap-2 text-xs font-mono text-text-secondary mb-3">
          <span>BLACK / SEEDED RANDOM</span><span>Recorded replay</span>
        </div>
        <div className="grid grid-cols-8 aspect-square overflow-hidden rounded-lg border border-border-highlight" role="img" aria-label={`Recorded chess position after ${ply} plies. ${move ? `${move.side} played ${move.san}.` : 'Starting position.'}`}>
          {squares(fen).map((piece, index) => {
            const file = index % 8;
            const rank = 8 - Math.floor(index / 8);
            const square = `${'abcdefgh'[file]}${rank}`;
            const light = (file + Math.floor(index / 8)) % 2 === 0;
            return (
              <div key={square} className={`relative grid place-items-center ${lastSquares.includes(square) ? 'bg-amber-300' : light ? 'bg-[#e6e2d7]' : 'bg-[#73847a]'}`} title={`${square}: ${piece ? `${piece === piece.toUpperCase() ? 'white' : 'black'} ${pieceNames[piece.toLowerCase()]}` : 'empty'}`}>
                <span className="text-[clamp(1.6rem,5vw,3.5rem)] leading-none text-[#171b19]" style={{ fontFamily: 'Georgia, serif' }} aria-hidden="true">{glyphs[piece] || ''}</span>
                {file === 0 && <span className="absolute top-0.5 left-1 text-[9px] font-mono text-black/70" aria-hidden="true">{rank}</span>}
                {rank === 1 && <span className="absolute bottom-0 right-1 text-[9px] font-mono text-black/70" aria-hidden="true">{'abcdefgh'[file]}</span>}
              </div>
            );
          })}
        </div>
        <div className="mt-3 text-xs font-mono text-text-secondary">WHITE / MALECNS CONNECTOME</div>
      </div>
      <div className="space-y-6">
        <div className="border-b border-border-subtle pb-5">
          <p className="text-xs uppercase tracking-[0.2em] text-accent font-mono mb-2">One completed trial</p>
          <p className="text-5xl font-display tracking-tight">0 <span className="text-text-secondary">—</span> 1</p>
          <p className="text-text-secondary mt-2">Connectome vs. seeded random. Checkmate at 93…Rg1#.</p>
        </div>
        <p className="text-text-secondary text-sm">Step through the actual 186 recorded plies. The playback speed is for browsing; it does not represent neural or wall-clock speed.</p>
        <div className="rounded-lg bg-white/5 p-4 font-mono text-sm" aria-live="polite" aria-atomic="true">
          {move ? `${Math.ceil(ply / 2)}${move.side === 'connectome' ? '.' : '…'} ${move.san} / ${move.side}` : 'Starting position'}
          <span className="block text-text-secondary mt-1">Ply {ply} of {game.moves.length}{ply === game.moves.length ? ' / checkmate' : ''}</span>
        </div>
        <input type="range" min={0} max={game.moves.length} value={ply} onChange={(event) => choosePly(Number(event.target.value))} className="w-full accent-amber-400" aria-label="Recorded move position" />
        <div className="flex flex-wrap gap-2">
          <button type="button" onClick={() => choosePly(Math.max(0, ply - 1))} disabled={ply === 0} className={buttonStyle}>Previous</button>
          <button type="button" onClick={() => { if (ply === game.moves.length) setPly(0); setPlaying(!playing || ply === game.moves.length); }} className={buttonStyle}>{playing && ply < game.moves.length ? 'Pause' : 'Play replay'}</button>
          <button type="button" onClick={() => choosePly(Math.min(game.moves.length, ply + 1))} disabled={ply === game.moves.length} className={buttonStyle}>Next</button>
          <button type="button" onClick={() => choosePly(game.moves.length)} className={buttonStyle}>Final position</button>
        </div>
        <p className="text-xs text-text-secondary">No living fly took part in this game. The board is reconstructed from saved FENs; moves were not generated for this webpage.</p>
      </div>
    </div>
  );
}
