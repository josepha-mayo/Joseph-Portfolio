import type { Metadata } from 'next';
import Image from 'next/image';
import Link from 'next/link';
import ChessReplay from './ChessReplay';

export const metadata: Metadata = {
  title: 'DOOMFLY — a fun project by Ayanda Joseph',
  description: 'A fly arena, a mapped connectome, Doom, and a chess board. A hands-on experiment in connecting biological signals to games, with the setup footage and honest results.',
};

const setupVideos = [
  { id: 1, title: 'The whole rig', duration: '35 sec', description: 'A walk around the desk: the arena, lighting, laptops, camera feed, and Doom windows.' },
  { id: 2, title: 'Inside the arena', duration: '38 sec', description: 'A close-up of the circular enclosure held between transparent plates and binder clips.' },
  { id: 3, title: 'Behind the scenes', duration: '15 sec', description: 'The container, workspace, lighting, and improvised physical setup around the experiment.' },
];

const doomRows = [
  ['Living-fly channel', '9,098', '3,758', 'Watched live; periodic drift'],
  ['Connectome + fly envelope', '8,832', '3,170', 'The fair comparison'],
  ['Connectome', '563', '6,527', 'Unconstrained run'],
  ['Random baseline', '8,468', '6,820', 'Game telemetry'],
];

function Section({ id, number, title, children }: { id: string; number: string; title: string; children: React.ReactNode }) {
  return (
    <section id={id} className="scroll-mt-28 border-t border-border-subtle py-16 md:py-24">
      <div className="mb-10 flex items-baseline gap-4">
        <span className="font-mono text-xs text-accent">{number}</span>
        <h2 className="font-display text-3xl md:text-4xl font-semibold tracking-tight">{title}</h2>
      </div>
      {children}
    </section>
  );
}

function Video({ src, poster, label, description, portrait = false }: { src: string; poster: string; label: string; description: string; portrait?: boolean }) {
  return (
    <figure>
      <video controls playsInline muted preload="none" poster={poster} aria-label={label} aria-describedby={`${label.replaceAll(' ', '-')}-description`} className={`w-full rounded-xl bg-black border border-border-highlight ${portrait ? 'aspect-[478/850] max-h-[520px]' : 'aspect-[3/2]'}`}>
        <source src={src} type="video/mp4" />
        Your browser does not support this video. <a href={src}>Download the clip</a>.
      </video>
      <figcaption id={`${label.replaceAll(' ', '-')}-description`} className="text-sm text-text-secondary mt-3 leading-relaxed">{description}</figcaption>
    </figure>
  );
}

export default function DoomflyPage() {
  return (
    <main id="main" className="min-h-screen bg-background">
      <nav className="fixed top-0 w-full h-[70px] nav-glass border-b border-border-subtle z-50" aria-label="Project navigation">
        <div className="max-w-6xl mx-auto px-6 md:px-8 h-full flex justify-between items-center gap-4">
          <Link href="/" className="font-display text-2xl font-bold" aria-label="Ayanda Joseph home">AJ<span className="text-accent">.</span></Link>
          <span className="hidden sm:block font-mono text-xs tracking-widest text-text-secondary">FIELD NOTES / SEPTEMBER 2026</span>
          <Link href="/#work" className="text-sm text-text-secondary hover:text-accent transition-colors">← all projects</Link>
        </div>
      </nav>

      <article className="max-w-6xl mx-auto px-6 md:px-8 pt-28 md:pt-36 pb-12">
        <header className="grid lg:grid-cols-[1.2fr_1fr] gap-10 lg:gap-16 items-center pb-16 md:pb-24">
          <div>
            <div className="flex flex-wrap items-center gap-3 mb-6 text-xs font-mono">
              <span className="rounded-full border border-accent/30 bg-accent/10 px-3 py-1 text-accent">Fun project</span>
              <span className="text-text-secondary">connectomics × games × a very real desk</span>
            </div>
            <p className="font-mono text-accent text-sm tracking-[0.3em] mb-3">DOOMFLY</p>
            <h1 className="font-display text-[clamp(2.8rem,6vw,5rem)] leading-[1.04] font-semibold tracking-tight">a fly, a brain map,<br />and <span className="text-accent">DOOM + chess.</span></h1>
            <p className="mt-7 text-lg text-text-secondary max-w-[48ch]">What happens when you connect a mapped fly nervous system to a game—and try to give a living fly the same controls?</p>
            <p className="mt-4 text-sm text-text-secondary max-w-[54ch]">Part desk experiment, part software rabbit hole. It started with Doom, reached a chess board, and taught me as much about measurement as it did about interfaces.</p>
            <div className="mt-8 flex flex-wrap gap-3">
              <a href="#setup" className="btn-primary rounded-md bg-accent text-background px-5 py-3 font-semibold text-sm">See the physical setup ↓</a>
              <a href="#chess" className="btn-ghost rounded-md border border-border-highlight px-5 py-3 text-sm">Replay the chess game</a>
            </div>
          </div>
          <figure className="relative">
            <div className="relative aspect-[4/5] overflow-hidden rounded-2xl border border-border-highlight bg-card">
              <Image src="/doomfly/setup-photo-1.jpg" alt="Overhead view of the physical fly arena: a circular enclosure between transparent plates held by binder clips, with the ring light reflected in the cover" fill priority sizes="(min-width: 1024px) 440px, 90vw" className="object-cover" />
              <div className="absolute bottom-0 inset-x-0 bg-gradient-to-t from-black/90 to-transparent px-6 pt-20 pb-6">
                <span className="font-mono text-xs text-accent">01 / THE HARDWARE</span>
                <p className="text-sm mt-2">Not a simulated fly trajectory.<br />An actual arena on my desk.</p>
              </div>
            </div>
            <figcaption className="text-xs text-text-secondary mt-3">The arena on my desk mid-session — the fly is the small speck inside the disc.</figcaption>
          </figure>
        </header>

        <div className="grid grid-cols-2 md:grid-cols-4 border-y border-border-subtle py-6 gap-6">
          {[
            ['166,700', 'retained neurons'], ['25.58M', 'retained graph edges'], ['Doom + chess', 'two game interfaces'], ['Experimental', 'not biological validation'],
          ].map(([value, label]) => <div key={label}><p className="font-display text-xl md:text-2xl">{value}</p><p className="text-xs text-text-secondary mt-1">{label}</p></div>)}
        </div>

        <div className="flex flex-wrap gap-x-6 gap-y-3 py-6 font-mono text-xs text-text-secondary" aria-label="On this page">
          {[['idea', '01 / the idea'], ['setup', '02 / physical setup'], ['notes', '03 / field notes'], ['doom', '04 / Doom'], ['chess', '05 / chess'], ['takeaways', '06 / what I learned']].map(([id, text]) => <a key={id} href={`#${id}`} className="hover:text-accent">{text}</a>)}
        </div>

        <Section id="idea" number="01" title="use the map. don’t invent the fly.">
          <div className="grid md:grid-cols-2 gap-10">
            <div className="space-y-5 text-text-secondary">
              <p className="text-xl text-text-primary">There are already mapped fly connectomes. We don’t need to invent a fake fly trajectory—or build our own game.</p>
              <p>The idea was to put two very different signal sources behind one game-control contract: a simulated network built from MaleCNS v1.0, and motion measured from a living fly in an overhead camera feed.</p>
              <p>Underneath it was a bigger curiosity. Where AI goes next probably isn’t only bigger models — people are already exploring biological substrates, neurons and cells as compute. This was my much smaller, desk-scale version of that idea: a reason to get my hands on physical, sophisticated hardware instead of only training models like I usually do.</p>
              <p>The connectome is the measured wiring map. Retinal projection, neuron dynamics, and the translation from descending-neuron activity into buttons are chosen modeling and engineering assumptions. A full retained graph is not a literal living brain.</p>
            </div>
            <div className="rounded-xl border border-border-highlight bg-card p-6 space-y-6">
              <div><h3 className="font-mono text-xs text-accent mb-3">MODELED PATH</h3><p className="text-sm leading-7">Game pixels → sensory input → full retained neural network → fixed descending-neuron decoder → controls</p></div>
              <div className="border-t border-border-subtle pt-5"><h3 className="font-mono text-xs text-accent mb-3">PHYSICAL PATH / ATTEMPTED</h3><p className="text-sm leading-7">Enclosed fly → overhead phone camera → position and movement tracking → the same control fields</p></div>
              <p className="text-xs text-text-secondary">The intended comparison was shared controls, not identical cognition. Reliable measurement was a prerequisite—and the physical arm did not meet it.</p>
            </div>
          </div>
        </Section>

        <Section id="setup" number="02" title="a small arena. a lot of cables.">
          <p className="text-text-secondary max-w-3xl mb-8">Transparent plates, a circular enclosure, binder clips, overhead illumination, my phone as the overhead camera (DroidCam), and my laptop generating the feedback signal shown to the fly. A small budget — the desk, some clips, and the principle that if something looks fun to try, I build it. These are my three physical-setup clips and still photographs, supplied on 15 September 2026. Web copies are silent and metadata-stripped; originals are preserved.</p>
          <div className="grid md:grid-cols-3 gap-7">
            {setupVideos.map((video) => <div key={video.id}>
              <div className="flex justify-between items-baseline gap-3 mb-3"><h3 className="font-display text-lg">{video.title}</h3><span className="font-mono text-xs text-text-secondary">{video.duration}</span></div>
              <Video src={`/doomfly/setup-${video.id}.mp4`} poster={`/doomfly/setup-${video.id}.jpg`} label={`Setup clip ${video.id}`} description={video.description} portrait />
            </div>)}
          </div>
          <div className="mt-10 grid lg:grid-cols-[1.15fr_1fr] gap-8 items-start">
            <figure>
              <div className="relative aspect-[4/3] overflow-hidden rounded-xl border border-border-highlight bg-card">
                <Image src="/doomfly/setup-photo-2.jpg" alt="The wider bench: the clip-mounted arena on a sheet of paper, a second dish with a tubing line, the phone, and cabling" fill sizes="(min-width: 1024px) 560px, 90vw" className="object-cover" />
              </div>
              <figcaption className="text-sm text-text-secondary mt-3 leading-relaxed">The wider bench: the clip-mounted arena, a second dish with a tubing line, the phone, and the cabling around it. Photographs document the apparatus — not a verified tracking lock.</figcaption>
            </figure>
            <div className="rounded-xl border border-border-subtle p-6 grid gap-6 text-sm">
              <div><h3 className="font-medium mb-2">Camera → controller</h3><p className="text-text-secondary">The phone watched the arena; the laptop turned tracked movement into the same control fields the connectome drove — position, heading, move and attack — and rendered the feedback signal.</p></div>
              <div><h3 className="font-medium mb-2">Game → feedback</h3><p className="text-text-secondary">A FlyVision page mapped the current game/control signals onto a nearby display. It was an engineered stimulus interface, not a claim about the fly’s subjective vision.</p></div>
              <div><h3 className="font-medium mb-2">Nothing aversive, nothing implanted</h3><p className="text-text-secondary">No electrodes, no shocks, no sound or electrical punishment anywhere in the loop. The fly’s own movement was the only input; light on a screen was the only feedback; sucrose was the only reward ever used.</p></div>
            </div>
          </div>
          <div className="mt-10 border-t border-border-subtle pt-8 grid md:grid-cols-3 gap-8 text-sm">
            <div>
              <h3 className="font-medium mb-2">Borrowed, not bought</h3>
              <p className="text-text-secondary">The flies came from teaching practicals — lab stock already on hand, not animals ordered for the project. Whatever signal the camera picked up was the whole experiment: movement in, controls out.</p>
            </div>
            <div>
              <h3 className="font-medium mb-2">Picking them up, putting them back</h3>
              <p className="text-text-secondary">A length of tubing doubled as a handheld aspirator — a gentle draw pulls a fly into the chamber, and it rides the airstream into the arena. When a session ended, the flies went back the same way.</p>
            </div>
            <div>
              <h3 className="font-medium mb-2">They kept to themselves after</h3>
              <p className="text-text-secondary">Back in the vial with its mates after a session, a fly didn’t go where the others were going — it stayed apart from the group. Inside the arena, stillness had to be logged as stillness too, never scored as a finished turn.</p>
            </div>
          </div>
        </Section>

        <Section id="notes" number="03" title="field notes — what the fly showed.">
          <div className="rounded-xl border border-border-subtle bg-card p-6 md:p-8 grid md:grid-cols-3 gap-8 text-sm">
            <div><h3 className="font-medium mb-2">Kept apart from its mates</h3><p className="text-text-secondary">Returned to the vial after sessions, the fly didn’t go where its mates were going — it stayed apart from the group. And inside the arena, a still fly produced no motion signal: stillness was logged as stillness, never as a finished turn. Quiet was data, not an ending.</p></div>
            <div><h3 className="font-medium mb-2">One substrate kept improving</h3><p className="text-text-secondary">Across later sessions the fly’s game-relevant signals got better — it arrived at useful behavior on its own. The connectome, once set up, was static. The shame of the small rig: the fly clearly carried far more usable signal than I could harness.</p></div>
            <div><h3 className="font-medium mb-2">Exploration before tailoring</h3><p className="text-text-secondary">Before the feedback signal was tuned toward the game, the fly roamed more of the arena. My own thought, not a result: once an agent knows enough, a constrained channel may reveal intent better than an open world — worth remembering for how we constrain models, even in RL, and note what they do.</p></div>
          </div>
        </Section>

        <Section id="doom" number="04" title="first stop: Doom.">
          <div className="grid md:grid-cols-2 gap-10 mb-10">
            <div className="space-y-4 text-text-secondary"><p>ViZDoom supplied the actual game. The modeled controller consumed game frames; the physical channel accepted measured-motion controls. The phone was the camera; my laptop decoded the fly’s movement into the shared control fields and generated the visual signal back to the fly.</p><p>The envelope arm constrained the connectome’s signal magnitudes and timing to recorded fly activity — that pairing, not the unrestricted run, is the fair comparison inside this setup.</p></div>
            <div className="space-y-6">
              <figure>
                <div className="relative aspect-[16/10] overflow-hidden rounded-xl border border-border-highlight bg-card">
                  <Image src="/doomfly/tracker-view.jpg" alt="The actual tracking view: the circular arena held by binder clips under the DroidCam feed, with the orientation marker near the left clip and the fly visible as a speck inside the disc" fill sizes="(min-width: 768px) 460px, 90vw" className="object-cover" />
                </div>
                <figcaption className="text-xs text-text-secondary mt-3 leading-relaxed">The real tracking view over DroidCam — arena bound, orientation marker, the fly a speck in the disc.</figcaption>
              </figure>
              <aside className="rounded-xl border border-accent/25 bg-accent/5 p-6"><h3 className="text-accent font-mono text-xs uppercase tracking-widest mb-3">The honest limitation</h3><p className="text-sm text-text-secondary">The marker stayed mostly on the fly, with periodic shifts onto clips and rim shadows — I was watching the feed and re-anchoring it. The deeper limit was bandwidth: the fly produced far more usable signal than this rig could capture, and that gap is the real story here.</p></aside>
            </div>
          </div>
          <div className="overflow-x-auto rounded-xl border border-border-subtle">
            <table className="w-full text-sm text-left whitespace-nowrap">
              <caption className="text-left px-5 py-4 text-text-secondary bg-card">Observed game-server counters inside this setup — coverage and protocols differ, so this is not a ranked benchmark.</caption>
              <thead className="bg-white/5 text-xs text-text-secondary"><tr><th scope="col" className="p-5 font-medium">Channel</th><th scope="col" className="p-5 font-medium">Observed episodes</th><th scope="col" className="p-5 font-medium">Observed kills*</th><th scope="col" className="p-5 font-medium">Reading</th></tr></thead>
              <tbody>{doomRows.map(([arm, episodes, kills, label]) => <tr key={arm} className="border-t border-border-subtle"><th scope="row" className="p-5 font-medium">{arm}</th><td className="p-5 font-mono">{episodes}</td><td className="p-5 font-mono">{kills}</td><td className="p-5 text-text-secondary">{label}</td></tr>)}</tbody>
            </table>
          </div>
          <p className="text-xs text-text-secondary mt-4">*Sum of available per-(run, episode) maximum kill counters, deduplicated. The fair pairing is the living fly versus the connectome under the fly’s own recorded envelope — and the living channel ran ahead (3,758 vs 3,170). Under matching signal constraints, the fly did more with the same budget; the unconstrained connectome outscored both only with a far richer signal path than any fly could ever drive.</p>
        </Section>

        <Section id="chess" number="05" title="then, a completely different board.">
          <div className="max-w-3xl text-text-secondary space-y-4 mb-10"><p>After the physical session, I ran a separate connectome-only chess experiment. This time, chess pixels—not recycled Doom actions—fed the network. The opponent was a seeded random legal-move sampler, not the living fly.</p><p>The living fly never got a board: the rig captured enough signal to steer Doom, not enough for 186 plies of menu navigation. That gap is itself part of the finding — the fly’s channel was real but thin.</p><p>A rendered board and sorted legal-move menu fed the existing retinal sampler and native neural model. Fixed decoded controls moved a menu cursor; neural attack activity selected an entry. The menu is an explicit interface aid, not chess strategy hidden inside the brain.</p></div>
          <div className="rounded-2xl border border-border-highlight bg-card p-4 md:p-8"><ChessReplay /></div>
          <div className="mt-10 grid lg:grid-cols-[1.3fr_1fr] gap-8 items-start">
            <Video src="/doomfly/chess-replay.mp4" poster="/doomfly/chess-replay.jpg" label="Neural selection replay" description="Recorded input snapshots and actual descending-neuron readout rates at each selection. This is a compressed snapshot replay, not real-time footage, a brain scan, or a living fly playing chess." />
            <div className="space-y-5 text-sm">
              <h3 className="font-display text-xl">What stayed fixed?</h3>
              <p className="text-text-secondary">All 166,700 retained neurons and 25,582,938 graph edges. The original baseline dynamics and BCI decoder. No fly-envelope handicap, no strategic engine, no reward current, no plasticity, and no learning during this chess run.</p>
              <p className="text-text-secondary">The RGB image was sampled as luminance at the existing receptor coordinates. Cursor movement used the fixed decoded turn/forward channels; selection had a 1,000-neural-ms UI interval. These choices are engineering, not measured fly chess behavior.</p>
              <p className="text-text-secondary">The final result was independently replay-checked for legal moves, PGN agreement, and matching saved input-frame hashes. One game against random moves does not establish chess skill.</p>
              <div className="flex flex-wrap gap-3 pt-2">
                <a href="/doomfly/match.pgn" download className="text-accent hover:underline underline-offset-4">Download all moves ↗</a>
                <a href="/doomfly/protocol.json" download className="text-accent hover:underline underline-offset-4">Run protocol ↗</a>
                <a href="/doomfly/summary.json" download className="text-accent hover:underline underline-offset-4">Result record ↗</a>
              </div>
            </div>
          </div>
          <div className="mt-10 grid lg:grid-cols-[1fr_1.3fr] gap-8 items-center">
            <figure>
              <div className="relative aspect-[4/5] overflow-hidden rounded-xl border border-border-highlight bg-[#151515]">
                <Image src="/doomfly/chess-interface.jpg" alt="The actual experiment interface during the completed game: the final checkmate board as an SVG, with the live match-state JSON below" fill sizes="(min-width: 1024px) 440px, 90vw" className="object-cover object-top" />
              </div>
              <figcaption className="text-xs text-text-secondary mt-3 leading-relaxed">The real experiment page at the end of the game — board SVG, recorded neural state, CHECKMATE 0–1.</figcaption>
            </figure>
            <div className="space-y-4 text-sm text-text-secondary">
              <h3 className="font-display text-xl text-text-primary">The page it actually ran on.</h3>
              <p>No dashboard, no styling pass — a monospace page serving the board and the raw match state while the connectome worked through the menu. What you see above is a reconstruction; this is the original interface as it ran.</p>
            </div>
          </div>
        </Section>

        <Section id="takeaways" number="06" title="the interesting part wasn’t winning.">
          <div className="grid md:grid-cols-3 gap-8">
            {[
              ['Measurement comes first.', 'A plausible trail can be a watermark. A fresh action can still be wrong. Verify the identity of the signal before interpreting the score.'],
              ['The interface is part of the experiment.', 'A legal-move menu makes a chess session possible, but changes what the task measures. State that choice instead of attributing it to the connectome.'],
              ['Keep the failures in the record.', 'The physical setup happened. The tracking limitations happened too. Retain the footage and telemetry without filling in missing results.'],
            ].map(([title, text]) => <div key={title} className="border-t border-border-highlight pt-5"><h3 className="font-display text-lg mb-3">{title}</h3><p className="text-text-secondary text-sm leading-relaxed">{text}</p></div>)}
          </div>
          <p className="mt-12 max-w-3xl text-lg text-text-secondary">A fun project, not a claim that I taught a fly to understand Doom or chess. The useful outcome is a traceable game interface, a completed neural-control chess record, a living channel that outperformed the envelope-matched connectome inside this rig, and a much clearer sense of what needs to be measured next.</p>
        </Section>

        <footer className="border-t border-border-subtle pt-8 flex flex-wrap justify-between gap-5 text-sm text-text-secondary">
          <Link href="/#work" className="hover:text-accent">← back to selected projects</Link>
          <span>Ayanda Joseph / DOOMFLY / September 2026</span>
        </footer>
      </article>
    </main>
  );
}
