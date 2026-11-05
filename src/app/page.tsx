'use client';

import Image from 'next/image';
import Link from 'next/link';
import { useState, useEffect } from 'react';
import Fireflies from '@/components/Fireflies';
import styles from './home.module.css';
import { featuredReleases, type FeaturedRelease } from './featured-releases';

function SkillGroup({ title, skills }: { title: string; skills: string[] }) {
  return <div className={styles.skillGroup}>
    <h3>{title}</h3>
    <div className={styles.skillTags}>{skills.map(skill => <span className={styles.skillTag} key={skill}>{skill}</span>)}</div>
  </div>;
}

function ProjectCard({ image, title, description, tags, links, award, index }: {
  image: string; title: string; description: string; tags: string[];
  links: { href: string; label: string; icon: string }[]; award?: string; index: number;
}) {
  return (
    <article className={styles.project}>
      <div className={styles.projectMedia}>
        <Image src={image} alt={title} fill sizes="(min-width: 1280px) 600px, (min-width: 640px) 50vw, 100vw" className={styles.projectImage} />
        {award && <span className={styles.award} aria-label={`${title}: ${award}`}><i className="fa-solid fa-trophy" aria-hidden="true" />{award}</span>}
      </div>
      <div className={styles.projectBody}>
        <div className={styles.projectTitle}><h3>{title}</h3><span aria-hidden="true">{String(index + 1).padStart(2, '0')}</span></div>
        <p className={styles.projectDescription}>{description}</p>
        <div className={styles.tags}>{tags.map(tag => <span className={tag === 'Fun project' ? styles.fun : undefined} key={tag}>{tag}</span>)}</div>
        <div className={styles.projectLinks}>
          {links.map(link => <Link key={link.href} href={link.href} target={link.href.startsWith('/') ? undefined : '_blank'} rel={link.href.startsWith('/') ? undefined : 'noopener noreferrer'}>
            <i className={link.icon} aria-hidden="true" />{link.label}
          </Link>)}
        </div>
      </div>
    </article>
  );
}

function ReleaseCard({ release }: { release: FeaturedRelease }) {
  const [downloads, setDownloads] = useState<number | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    async function refreshDownloads() {
      try {
        const response = await fetch(`https://huggingface.co/api/${release.type}s/${release.repo}?expand=downloadsAllTime`, { signal: controller.signal });
        if (!response.ok) return;
        const data = await response.json();
        if (typeof data.downloadsAllTime === 'number' && Number.isFinite(data.downloadsAllTime) && data.downloadsAllTime >= 0) {
          setDownloads(data.downloadsAllTime);
        }
      } catch {
        // Keep the dated snapshot if Hugging Face is unavailable.
      }
    }
    void refreshDownloads();
    return () => controller.abort();
  }, [release.repo, release.type]);

  return <article className={styles.release}>
    <p className={styles.releaseKind}>{release.kind}</p>
    <h3>{release.name}</h3>
    <p className={styles.releaseDescription}>{release.description}</p>
    <div className={styles.result}>
      <strong>{release.result}</strong>
      <span>{release.scope}</span>
      <a href={release.evidenceUrl} target="_blank" rel="noopener noreferrer" aria-label={`${release.name}: evaluation & scope`}>evaluation &amp; scope ↗</a>
    </div>
    <p className={styles.downloads}>
      {(downloads ?? release.downloads).toLocaleString('en-US')} {release.downloadLabel}
      <br /><span className={styles.downloadSource}>all time · {downloads === null ? 'snapshot: 5 Nov 2026' : 'via Hugging Face'}</span>
    </p>
    <div className={styles.releaseLinks}>
      {release.links.map(link => <a key={link.url} href={link.url} target="_blank" rel="noopener noreferrer">{link.label}<span aria-hidden="true">↗</span></a>)}
    </div>
  </article>;
}

export default function Home() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const projects = [
    {
      image: "/doomfly/setup-photo-1.jpg",
      title: "DOOMFLY",
      description: "A physical fly arena, a Doom experiment, and 93 moves of connectome chess. Replay the game and inspect the measurement failures.",
      tags: ["Fun project", "connectomics", "OpenCV", "Doom + chess"],
      links: [
        { href: "/doomfly", label: "explore the experiment", icon: "fa-solid fa-arrow-right" }
      ]
    },
    {
      image: "/projects/dr-opic-pipeline.svg",
      title: "DR-OPIC",
      description: "A coding SLM training framework: attempt, test, repair, then train on the corrected spans. Verified repairs feed a difficulty-aware curriculum.",
      tags: ["python", "SLM training", "PyTorch", "verifier"],
      links: [
        { href: "/dr-opic", label: "read the method", icon: "fa-solid fa-arrow-right" },
        { href: "https://github.com/josepha-mayo/DR-OPIC", label: "source", icon: "fa-brands fa-github" }
      ]
    },
    {
      image: "/vector_projection.png",
      title: "Model Unfetter",
      description: "A weight-space ablation engine for studying LLM refusal directions, with evaluation tools to check the effects on model behavior.",
      tags: ["python", "red teaming", "research"],
      links: [
        { href: "/model-ablation", label: "read the method", icon: "fa-solid fa-arrow-right" },
        { href: "https://github.com/josepha-mayo/model-unfetter", label: "source", icon: "fa-brands fa-github" }
      ]
    },
    {
      image: "/swarms.png",
      title: "SWARMs Debate Primitive",
      award: "Won",
      description: "Agents debate from distinct personas and vote on an answer. Session transcript hashes are recorded on Solana for an auditable record.",
      tags: ["Python", "Solana", "multi-agent", "blockchain"],
      links: [
        { href: "https://github.com/josepha-mayo/SWARMs-Debate-Primitive", label: "source", icon: "fa-brands fa-github" }
      ]
    },
    {
      image: "/intellectsafe.png",
      title: "IntellectSafe",
      description: "A multi-model council and proxy for frontier models, alongside deepfake detection and adversarial defense tools.",
      tags: ["fastAPI", "next.js", "security"],
      links: [
        { href: "https://intellect-safe.vercel.app", label: "live demo", icon: "fa-solid fa-arrow-up-right-from-square" },
        { href: "https://github.com/josepha-mayo/IntellectSafe", label: "source", icon: "fa-brands fa-github" }
      ]
    },
    {
      image: "/modelfang.png",
      title: "ModelFang",
      description: "Graph-based LLM red teaming with multi-turn attacks, a state-machine evaluator, and a dashboard for inspecting results.",
      tags: ["python", "next.js", "red teaming"],
      links: [
        { href: "https://model-fang.vercel.app", label: "live demo", icon: "fa-solid fa-arrow-up-right-from-square" },
        { href: "https://github.com/josepha-mayo/ModelFang", label: "source", icon: "fa-brands fa-github" }
      ]
    },
    {
      image: "/projects/mayo-pipeline.svg",
      title: "Mayo",
      description: "Three agents scan code, make edits, and review the changes before opening a PR. Cross-repository memory carries findings between runs.",
      tags: ["python", "agentic AI", "GitHub"],
      links: [
        { href: "https://github.com/josepha-mayo/mayo", label: "source", icon: "fa-brands fa-github" }
      ]
    },
    {
      image: "/projects/pex-screenshot.webp",
      title: "PEX",
      description: "An inference-backed agent that keeps coding agents working toward persistent goals. Model reviews, a claim ledger, and independent tests check whether the work is actually done.",
      tags: ["agentic AI", "model inference", "verification"],
      links: [
        { href: "https://pex-supervisor.netlify.app", label: "live demo", icon: "fa-solid fa-arrow-up-right-from-square" },
        { href: "https://github.com/josepha-mayo/pex", label: "source", icon: "fa-brands fa-github" }
      ]
    },
    {
      image: "/projects/socbench-screenshot.webp",
      title: "Socbench",
      description: "Dataset intelligence with 55 catalogued datasets, 53 automated assessments, and 16 proxy-training outcomes, including six divergent runs retained as evidence.",
      tags: ["next.js", "fastAPI", "data quality", "evaluation"],
      links: [
        { href: "https://github.com/josepha-mayo/socbench", label: "source & evidence", icon: "fa-brands fa-github" }
      ]
    },
    {
      image: "/projects/gitpulse.png",
      title: "gitPulse",
      description: "A social feed for developers to share updates, publish releases, and follow builders. GitHub sign-in, public feeds, and live updates.",
      tags: ["next.js", "typeScript", "postgreSQL", "full-stack"],
      links: [
        { href: "https://hubfeed.netlify.app", label: "live app", icon: "fa-solid fa-arrow-up-right-from-square" },
        { href: "https://github.com/josepha-mayo/git-pulse", label: "source", icon: "fa-brands fa-github" }
      ]
    }
  ];

  return (
    <>
      {/* Navigation */}
      <nav className="fixed top-0 w-full h-[70px] nav-glass border-b border-border-subtle z-50 flex items-center" aria-label="primary" onKeyDown={event => { if (event.key === 'Escape') setMobileMenuOpen(false); }}>
        <div className={`${styles.shell} flex justify-between items-center`}>
          <a href="#" className="font-display text-2xl font-bold text-text-primary">
            AJ<span className="text-accent">.</span>
          </a>

          <ul className="hidden lg:flex items-center gap-8 list-none">
            <li><a href="#about" className="text-text-secondary hover:text-text-primary text-[15px] font-medium transition-colors">about</a></li>
            <li><a href="#skills" className="text-text-secondary hover:text-text-primary text-[15px] font-medium transition-colors">tech stack</a></li>
            <li><a href="#work" className="text-text-secondary hover:text-text-primary text-[15px] font-medium transition-colors">work</a></li>
            <li><a href="#contact" className="text-text-secondary hover:text-text-primary text-[15px] font-medium transition-colors">contact</a></li>
            <li><a href="/Joseph_Ayanda_CV.pdf" download="Joseph_Ayanda_CV.pdf" aria-label="Download CV (PDF)" className="text-accent hover:text-text-primary text-[15px] font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent">cv <i className="fa-solid fa-arrow-down text-xs" aria-hidden="true"></i></a></li>
            <li className="flex gap-4 ml-4 pl-4 border-l border-border-subtle">
              <a href="https://github.com/josepha-mayo" aria-label="GitHub" target="_blank" className="text-text-secondary hover:text-text-primary text-lg transition-colors">
                <i className="fa-brands fa-github"></i>
              </a>
              <a href="https://huggingface.co/josephmayo" target="_blank" className="text-text-secondary hover:text-text-primary text-lg transition-colors flex items-center justify-center" title="HuggingFace">
                <svg fill="currentColor" fillRule="evenodd" height="1em" style={{flex:'none',lineHeight:1}} viewBox="0 0 24 24" width="1em" xmlns="http://www.w3.org/2000/svg"><title>HuggingFace</title><path d="M16.781 3.277c2.997 1.704 4.844 4.851 4.844 8.258 0 .995-.155 1.955-.443 2.857a1.332 1.332 0 011.125.4 1.41 1.41 0 01.2 1.723c.204.165.352.385.428.632l.017.062c.06.222.12.69-.2 1.166.244.37.279.836.093 1.236-.255.57-.893 1.018-2.128 1.5l-.202.078-.131.048c-.478.173-.89.295-1.061.345l-.086.024c-.89.243-1.808.375-2.732.394-1.32 0-2.3-.36-2.923-1.067a9.852 9.852 0 01-3.18.018C9.778 21.647 8.802 22 7.494 22a11.249 11.249 0 01-2.541-.343l-.221-.06-.273-.08a16.574 16.574 0 01-1.175-.405c-1.237-.483-1.875-.93-2.13-1.501-.186-.4-.151-.867.093-1.236a1.42 1.42 0 01-.2-1.166c.069-.273.226-.516.447-.694a1.41 1.41 0 01.2-1.722c.233-.248.557-.391.917-.407l.078-.001a9.385 9.385 0 01-.44-2.85c0-3.407 1.847-6.554 4.844-8.258a9.822 9.822 0 019.687 0zM4.188 14.758c.125.687 2.357 2.35 2.14 2.707-.19.315-.796-.239-.948-.386l-.041-.04-.168-.147c-.561-.479-2.304-1.9-2.74-1.432-.43.46.119.859 1.055 1.42l.784.467.136.083c1.045.643 1.12.84.95 1.113-.188.295-3.07-2.1-3.34-1.083-.27 1.011 2.942 1.304 2.744 2.006-.2
                .7-2.265-1.324-2.685-.537-.425.79 2.913 1.718 2.94 1.725l.16.04.175.042c1.227.284 3.565.65 4.435-.604.673-.973.64-1.709-.248-2.61l-.057-.057c-.945-.928-1.495-2.288-1.495-2.288l-.017-.058-.025-.072c-.082-.22-.284-.639-.63-.584-.46.073-.798 1.21.12 1.933l.05.038c.977.721-.195 1.21-.573.534l-.058-.104-.143-.25c-.463-.799-1.282-2.111-1.739-2.397-.532-.332-.907-.148-.782.541zm14.842-.541c-.533.335-1.563 2.074-1.94 2.751a.613.613 0 01-.687.302.436.436 0 01-.176-.098.303.303 0 01-.049-.06l-.014-.028-.008-.02-.007-.019-.003-.013-.003-.017a.289.289 0 01-.004-.048c0-.12.071-.266.25-.427.026-.024.054-.047.084-.07l.047-.036c.022-.016.043-.032.063-.049.883-.71.573-1.81.131-1.917l-.031-.006-.056-.004a.368.368 0 00-.062.006l-.028.005-.042.014-.039.017-.028.015-.028.019-.036.027-.023.02c-.173.158-.273.428-.31.542l-.016.054s-.53 1.309-1.439 2.234l-.054.054c-.365.358-.596.69-.702 1.018-.143.437-.066.868.21 1.353.055.097.117.195.187.296.882 1.275 3.282.876 4.494.59l.286-.07.25-.074c.276-.084.736-.233 1.2-.42l.188-.077.065-.028.064-.028.124-.056.081-.038c.529-.252.964-.543.994-.827l.001-.036a.299.299 0 00-.037-.139c-.094-.176-.271-.212-.491-.168l-.045.01c-.044.01-.09.024-.136.04l-.097.035-.054.022c-.559.23-1.238.705-1.607.745h.006a.452.452 0 01-.05.003h-.024l-.024-.003-.023-.005c-.068-.016-.116-.06-.14-.142a.22.22 0 01-.005-.1c.062-.345.958-.595 1.713-.91l.066-.028c.528-.224.97-.483.985-.832v-.04a.47.47 0 00-.016-.098c-.048-.18-.175-.251-.36-.251-.785 0-2.55 1.36-2.92 1.36-.025 0-.048-.007-.058-.024a.6.6 0 01-.046-.088c-.1-.238.068-.462 1.06-1.066l.209-.126c.538-.32 1.01-.588 1.341-.831.29-.212.475-.406.503-.6l.003-.028c.008-.113-.038-.227-.147-.344a.266.266 0 00-.07-.054l-.034-.015-.013-.005a.403.403 0 00-.13-.02c-.162 0-.369.07-.595.18-.637.313-1.431.952-1.826 1.285l-.249.215-.033.033c-.08.078-.288.27-.493.386l-.071.037-.041.019a.535.535 0 01-.122.036h.005a.346.346 0 01-.031.003l.01-.001-.013.001c-.079.005-.145-.021-.19-.095a.113.113 0 01-.014-.065c.027-.465 2.034-1.991 2.152-2.642l.009-.048c.1-.65-.271-.817-.791-.493zM11.938 2.984c-4.798 0-8.688 3.829-8.688 8.55 0 .692.083 1.364.24 2.008l.008-.009c.252-.298.612-.46 1.017-.46.355.008.699.117.993.312.22.14.465.384.715.694.261-.372.69-.598 1.15-.605.852 0 1.367.728 1.562 1.383l.047.105.06.127c.192.396.595 1.139 1.143 1.68 1.06 1.04 1.324 2.115.8 3.266a8.865 8.865 0 002.024-.014c-.505-1.12-.26-2.17.74-3.186l.066-.066c.695-.684 1.157-1.69 1.252-1.912.195-.655.708-1.383 1.56-1.383.46.007.889.233 1.15.605.25-.31.495-.553.718-.694a1.87 1.87 0 01.99-.312c.357 0 .682.126.925.36.14-.61.215-1.245.215-1.898 0-4.722-3.89-8.55-8.687-8.55zm1.857 8.926l.439-.212c.553-.264.89-.383.89.152 0 1.093-.771 3.208-3.155 3.262h-.184c-2.325-.052-3.116-2.06-3.156-3.175l-.001-.087c0-1.107 1.452.586 3.25.586.716 0 1.379-.272 1.917-.526zm4.017-3.143c.45 0 .813.358.813.8 0 .441-.364.8-.813.8a.806.806 0 01-.812-.8c0-.442.364-.8.812-.8zm-11.624 0c.448 0 .812.358.812.8 0 .441-.364.8-.812.8a.806.806 0 01-.813-.8c0-.442.364-.8.813-.8zm7.79-.841c.32-.384.846-.54 1.33-.394.483.146.83.564.878 1.06.048.495-.212.97-.659 1.203-.322.168-.447-.477-.767-.585l.002-.003c-.287-.098-.772.362-.925.079a1.215 1.215 0 01.14-1.36zm-4.323 0c.322.384.377.92.14 1.36-.152.283-.64-.177-.925-.079l.003.003c-.108.036-.194.134-.273.24l-.118.165c-.11.15-.22.262-.377.18a1.226 1.226 0 01-.658-1.204c.048-.495.395-.913.878-1.059a1.262 1.262 0 011.33.394z"></path></svg>
              </a>
              <a href="https://x.com/josepha_mayo" aria-label="X" target="_blank" className="text-text-secondary hover:text-text-primary text-lg transition-colors">
                <i className="fa-brands fa-x-twitter"></i>
              </a>
              <a href="mailto:ayandajoseph390@gmail.com" aria-label="email Joseph" className="text-text-secondary hover:text-text-primary text-lg transition-colors">
                <i className="fa-solid fa-envelope"></i>
              </a>
            </li>
          </ul>

          <button className="lg:hidden text-text-primary text-2xl bg-transparent border-none cursor-pointer w-11 h-11" aria-label={mobileMenuOpen ? 'close navigation' : 'open navigation'} aria-expanded={mobileMenuOpen} aria-controls="mobile-navigation" onClick={() => setMobileMenuOpen(open => !open)}>
            <i className={mobileMenuOpen ? 'fa-solid fa-xmark' : 'fa-solid fa-bars'} aria-hidden="true"></i>
          </button>
        </div>
        {mobileMenuOpen && <div id="mobile-navigation" className={styles.mobileMenu}>
          <div className={styles.shell}>
            {[['#about', 'about'], ['#skills', 'tools & methods'], ['#work', 'projects'], ['#models', 'models & datasets'], ['#contact', 'contact']].map(([href, label]) => <a key={href} href={href} onClick={() => setMobileMenuOpen(false)}>{label}</a>)}
            <a href="/Joseph_Ayanda_CV.pdf" download onClick={() => setMobileMenuOpen(false)}>download CV ↓</a>
          </div>
        </div>}
      </nav>

      <main id="main">
      {/* Hero Section */}
      <header
        className="min-h-[100dvh] flex items-end pt-[100px] pb-64 md:pb-44 relative overflow-hidden hero-grain"
        style={{
          background: 'linear-gradient(to bottom, rgba(10,10,10,0.78), rgba(10,10,10,0.95)), url(/image.jpg)',
          backgroundSize: 'cover',
          backgroundPosition: 'center'
        }}
      >
        <div className={`${styles.shell} z-10`}>
          <div className="grid md:grid-cols-12 gap-10 items-start">
            <div className="md:col-span-7 md:pt-24">
              <h1 className="font-display text-[clamp(2.25rem,6vw,4.5rem)] font-semibold leading-[1.02] tracking-tight mb-4 text-text-primary animate-slide-up animate-slide-up-delay-1 max-w-5xl">
                ai/ml engineer
              </h1>

              <p className="text-lg md:text-xl text-text-secondary max-w-[58ch] mb-5 animate-slide-up animate-slide-up-delay-2">
                i train and fine tune language models, publish open weights and datasets, and build tools for model evaluation and red teaming.
              </p>

              <div className="flex flex-wrap gap-3 animate-slide-up animate-slide-up-delay-3">
                <a href="#work" className="btn-primary inline-flex items-center gap-2 px-5 py-3 rounded-md font-medium bg-white text-background hover:bg-zinc-200 no-underline">
                  see selected work <i className="fa-solid fa-arrow-right text-xs"></i>
                </a>
                <a href="#models" className="btn-ghost inline-flex items-center gap-2 px-5 py-3 rounded-md font-medium text-text-primary border border-border-subtle hover:border-border-highlight no-underline">
                  browse open models
                </a>
                <a href="#contact" className="btn-ghost inline-flex items-center gap-2 px-5 py-3 rounded-md font-medium text-text-secondary hover:text-text-primary no-underline">
                  get in touch
                </a>
              </div>

            </div>

            <div className="md:col-span-5 hidden md:block animate-slide-up animate-slide-up-delay-3">
              <div className="relative left-20">
                <Fireflies />
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* About Section */}
      <section id="about" className="py-32 md:py-40">
        <div className={styles.shell}>
          <div className="mb-16">
            <h2 className="text-3xl md:text-4xl font-display font-semibold tracking-tight">about</h2>
          </div>

          <div className="grid md:grid-cols-2 gap-12 items-start">
            <div className="space-y-6">
              <p className="text-text-secondary text-lg max-w-[58ch]">
                i&apos;m an <span className="text-text-primary font-medium">ai/ml engineer</span> working at the intersection of model training, red teaming, and open-source tooling.
              </p>
              <p className="text-text-secondary text-lg max-w-[58ch]">
                day to day: fine-tuning and quantizing language models, running red teaming and refusal-direction work, and building tools around them. local-first models when they make sense, hosted apis when they don&apos;t.
              </p>
              <p className="text-text-primary text-lg max-w-[58ch] border-l-2 border-accent pl-4">
                mostly experiments, debugging, and building tools for problems i&apos;ve run into myself.
              </p>
            </div>

            <div className="mission-card rounded-2xl px-5 pt-8 pb-10 sm:px-6 md:px-8 md:pb-12 min-h-[25rem] border border-border-subtle relative overflow-hidden bg-card">
              <svg
                className="absolute inset-0 w-full h-full mission-card-bg"
                viewBox="0 49 399 305"
                preserveAspectRatio="xMidYMin slice"
                aria-hidden="true"
                style={{ filter: 'brightness(0.20) contrast(1.02)' }}
              >
                <image href="/personal/joe-about.jpg" width="399" height="399" />
              </svg>
              <div className="absolute inset-0 bg-black/35 mission-card-overlay" />
              <div className="relative z-10 mission-card-content">
                <h3 className="mb-6 text-white text-xl">
                  <i className="fa-solid fa-bullseye text-accent mr-2"></i> core mission
                </h3>
                <ul className="list-none flex flex-col gap-4 text-zinc-100">
                  <li className="flex items-start gap-2">
                    <i className="fa-solid fa-check text-accent mt-1 w-4 shrink-0" aria-hidden="true"></i>
                    <span className="min-w-0">ML engineering & research</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <i className="fa-solid fa-check text-accent mt-1 w-4 shrink-0" aria-hidden="true"></i>
                    <span className="min-w-0">adversarial testing</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <i className="fa-solid fa-check text-accent mt-1 w-4 shrink-0" aria-hidden="true"></i>
                    <span className="min-w-0">evaluation</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <i className="fa-solid fa-check text-accent mt-1 w-4 shrink-0" aria-hidden="true"></i>
                    <span className="min-w-0">agentic systems</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <i className="fa-solid fa-check text-accent mt-1 w-4 shrink-0" aria-hidden="true"></i>
                    <span className="min-w-0">dataset curation & synthetic data</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <i className="fa-solid fa-check text-accent mt-1 w-4 shrink-0" aria-hidden="true"></i>
                    <span className="min-w-0">local AI</span>
                  </li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section id="skills" className={styles.section}>
        <div className={styles.shell}>
          <div className={styles.sectionHead}><h2>tools &amp; methods</h2><p>what i work with</p></div>
          <div className={styles.skills}>
            <SkillGroup title="model training" skills={['PyTorch', 'Transformers', 'LoRA / QLoRA', 'DPO / ORPO', 'GGUF']} />
            <SkillGroup title="evaluation & red teaming" skills={['refusal ablation', 'adversarial testing', 'execution verifiers', 'model evaluation']} />
            <SkillGroup title="data" skills={['dataset curation', 'synthetic data', 'quality filtering', 'deduplication']} />
            <SkillGroup title="languages" skills={['Python', 'TypeScript', 'C']} />
            <SkillGroup title="applications" skills={['Next.js', 'FastAPI', 'Node.js', 'PostgreSQL', 'Redis']} />
            <SkillGroup title="infrastructure" skills={['Docker', 'GitHub', 'Cloudflare', 'Prime Intellect']} />
          </div>
        </div>
      </section>

      <section id="work" className={styles.section}>
        <div className={styles.shell}>
          <div className={styles.sectionHead}><h2>selected projects</h2><p>research, experiments &amp; shipped tools</p></div>
          <div className={styles.projects}>
            {projects.map((project, index) => <ProjectCard key={project.title} {...project} index={index} />)}
          </div>
          <div className={styles.allProjects}><a href="https://github.com/josepha-mayo?tab=repositories" target="_blank" rel="noopener noreferrer">all projects on GitHub <span aria-hidden="true">↗</span></a></div>
        </div>
      </section>

      <section id="models" className={styles.section}>
        <div className={styles.shell}>
          <div className={styles.sectionHead}>
            <h2>models &amp; datasets</h2>
            <a href="https://huggingface.co/josephmayo" target="_blank" rel="noopener noreferrer">all releases on Hugging Face ↗</a>
          </div>
          <p className={styles.sectionIntro}>a selection of coding models, refusal research, and training data. related weights and quantizations share one entry.</p>
          <div className={styles.releases}>
            {featuredReleases.map(release => <ReleaseCard key={release.repo} release={release} />)}
          </div>
          <p className={styles.releaseNote}>Results are reported in the linked release notes, with each evaluation&apos;s scope shown above. Different evaluations are not directly comparable. Download counts refer to the named model, GGUF release, or dataset individually.</p>
        </div>
      </section>

      <section id="drive" aria-labelledby="drive-heading" className="py-10 md:py-12 border-t border-border-subtle">
        <div className="container mx-auto px-6 md:px-8 max-w-6xl">
          <div className="max-w-4xl mx-auto">
            <h2 id="drive-heading" className="text-mono text-xs text-accent mb-4">drive</h2>
            <figure>
              <blockquote className="font-display text-base md:text-lg leading-relaxed text-text-primary max-w-3xl">
                <p>&ldquo;let it offend you that someone else can be handed your days and turn them into something greater&rdquo;</p>
              </blockquote>
              <figcaption className="mt-3 text-xs text-text-secondary">seneca</figcaption>
            </figure>
          </div>
        </div>
      </section>
      </main>

      {/* Footer */}
      <footer id="contact" className="bg-card border-t border-border-subtle py-16 text-center">
        <div className={styles.shell}>
          <div className="mb-14 flex items-center justify-end border-b border-border-subtle pb-7">
            <Link
              href="/outside-the-work"
              className="btn-ghost inline-flex shrink-0 items-center gap-2 rounded-md border border-zinc-700/70 bg-zinc-900 px-3.5 py-2 text-xs font-medium text-zinc-200 hover:border-zinc-500 hover:bg-zinc-800 hover:text-white"
            >
              outside the lab <span aria-hidden="true">↗</span>
            </Link>
          </div>
          <h2 className="mb-8 text-3xl">let&apos;s work on something useful</h2>
          <div className="flex justify-center gap-8 mb-8">
            <a href="https://github.com/josepha-mayo" aria-label="GitHub" target="_blank" className="text-text-secondary hover:text-text-primary text-2xl transition-all hover:-translate-y-1">
              <i className="fa-brands fa-github"></i>
            </a>
            <a href="https://huggingface.co/josephmayo" target="_blank" className="text-text-secondary hover:text-text-primary text-2xl transition-all hover:-translate-y-1 flex items-center justify-center" title="HuggingFace">
              <svg fill="currentColor" fillRule="evenodd" height="1em" style={{flex:'none',lineHeight:1}} viewBox="0 0 24 24" width="1em" xmlns="http://www.w3.org/2000/svg"><title>HuggingFace</title><path d="M16.781 3.277c2.997 1.704 4.844 4.851 4.844 8.258 0 .995-.155 1.955-.443 2.857a1.332 1.332 0 011.125.4 1.41 1.41 0 01.2 1.723c.204.165.352.385.428.632l.017.062c.06.222.12.69-.2 1.166.244.37.279.836.093 1.236-.255.57-.893 1.018-2.128 1.5l-.202.078-.131.048c-.478.173-.89.295-1.061.345l-.086.024c-.89.243-1.808.375-2.732.394-1.32 0-2.3-.36-2.923-1.067a9.852 9.852 0 01-3.18.018C9.778 21.647 8.802 22 7.494 22a11.249 11.249 0 01-2.541-.343l-.221-.06-.273-.08a16.574 16.574 0 01-1.175-.405c-1.237-.483-1.875-.93-2.13-1.501-.186-.4-.151-.867.093-1.236a1.42 1.42 0 01-.2-1.166c.069-.273.226-.516.447-.694a1.41 1.41 0 01.2-1.722c.233-.248.557-.391.917-.407l.078-.001a9.385 9.385 0 01-.44-2.85c0-3.407 1.847-6.554 4.844-8.258a9.822 9.822 0 019.687 0zM4.188 14.758c.125.687 2.357 2.35 2.14 2.707-.19.315-.796-.239-.948-.386l-.041-.04-.168-.147c-.561-.479-2.304-1.9-2.74-1.432-.43.46.119.859 1.055 1.42l.784.467.136.083c1.045.643 1.12.84.95 1.113-.188.295-3.07-2.1-3.34-1.083-.27 1.011 2.942 1.304 2.744 2.006-.2.7-2.265-1.324-2.685-.537-.425.79 2.913 1.718 2.94 1.725l.16.04.175.042c1.227.284 3.565.65 4.435-.604.673-.973.64-1.709-.248-2.61l-.057-.057c-.945-.928-1.495-2.288-1.495-2.288l-.017-.058-.025-.072c-.082-.22-.284-.639-.63-.584-.46.073-.798 1.21.12 1.933l.05.038c.977.721-.195 1.21-.573.534l-.058-.104-.143-.25c-.463-.799-1.282-2.111-1.739-2.397-.532-.332-.907-.148-.782.541zm14.842-.541c-.533.335-1.563 2.074-1.94 2.751a.613.613 0 01-.687.302.436.436 0 01-.176-.098.303.303 0 01-.049-.06l-.014-.028-.008-.02-.007-.019-.003-.013-.003-.017a.289.289 0 01-.004-.048c0-.12.071-.266.25-.427.026-.024.054-.047.084-.07l.047-.036c.022-.016.043-.032.063-.049.883-.71.573-1.81.131-1.917l-.031-.006-.056-.004a.368.368 0 00-.062.006l-.028.005-.042.014-.039.017-.028.015-.028.019-.036.027-.023.02c-.173.158-.273.428-.31.542l-.016.054s-.53 1.309-1.439 2.234l-.054.054c-.365.358-.596.69-.702 1.018-.143.437-.066.868.21 1.353.055.097.117.195.187.296.882 1.275 3.282.876 4.494.59l.286-.07.25-.074c.276-.084.736-.233 1.2-.42l.188-.077.065-.028.064-.028.124-.056.081-.038c.529-.252.964-.543.994-.827l.001-.036a.299.299 0 00-.037-.139c-.094-.176-.271-.212-.491-.168l-.045.01c-.044.01-.09.024-.136.04l-.097.035-.054.022c-.559.23-1.238.705-1.607.745h.006a.452.452 0 01-.05.003h-.024l-.024-.003-.023-.005c-.068-.016-.116-.06-.14-.142a.22.22 0 01-.005-.1c.062-.345.958-.595 1.713-.91l.066-.028c.528-.224.97-.483.985-.832v-.04a.47.47 0 00-.016-.098c-.048-.18-.175-.251-.36-.251-.785 0-2.55 1.36-2.92 1.36-.025 0-.048-.007-.058-.024a.6.6 0 01-.046-.088c-.1-.238.068-.462 1.06-1.066l.209-.126c.538-.32 1.01-.588 1.341-.831.29-.212.475-.406.503-.6l.003-.028c.008-.113-.038-.227-.147-.344a.266.266 0 00-.07-.054l-.034-.015-.013-.005a.403.403 0 00-.13-.02c-.162 0-.369.07-.595.18-.637.313-1.431.952-1.826 1.285l-.249.215-.033.033c-.08.078-.288.27-.493.386l-.071.037-.041.019a.535.535 0 01-.122.036h.005a.346.346 0 01-.031.003l.01-.001-.013.001c-.079.005-.145-.021-.19-.095a.113.113 0 01-.014-.065c.027-.465 2.034-1.991 2.152-2.642l.009-.048c.1-.65-.271-.817-.791-.493zM11.938 2.984c-4.798 0-8.688 3.829-8.688 8.55 0 .692.083 1.364.24 2.008l.008-.009c.252-.298.612-.46 1.017-.46.355.008.699.117.993.312.22.14.465.384.715.694.261-.372.69-.598 1.15-.605.852 0 1.367.728 1.562 1.383l.047.105.06.127c.192.396.595 1.139 1.143 1.68 1.06 1.04 1.324 2.115.8 3.266a8.865 8.865 0 002.024-.014c-.505-1.12-.26-2.17.74-3.186l.066-.066c.695-.684 1.157-1.69 1.252-1.912.195-.655.708-1.383 1.56-1.383.46.007.889.233 1.15.605.25-.31.495-.553.718-.694a1.87 1.87 0 01.99-.312c.357 0 .682.126.925.36.14-.61.215-1.245.215-1.898 0-4.722-3.89-8.55-8.687-8.55zm1.857 8.926l.439-.212c.553-.264.89-.383.89.152 0 1.093-.771 3.208-3.155 3.262h-.184c-2.325-.052-3.116-2.06-3.156-3.175l-.001-.087c0-1.107 1.452.586 3.25.586.716 0 1.379-.272 1.917-.526zm4.017-3.143c.45 0 .813.358.813.8 0 .441-.364.8-.813.8a.806.806 0 01-.812-.8c0-.442.364-.8.812-.8zm-11.624 0c.448 0 .812.358.812.8 0 .441-.364.8-.812.8a.806.806 0 01-.813-.8c0-.442.364-.8.813-.8zm7.79-.841c.32-.384.846-.54 1.33-.394.483.146.83.564.878 1.06.048.495-.212.97-.659 1.203-.322.168-.447-.477-.767-.585l.002-.003c-.287-.098-.772.362-.925.079a1.215 1.215 0 01.14-1.36zm-4.323 0c.322.384.377.92.14 1.36-.152.283-.64-.177-.925-.079l.003.003c-.108.036-.194.134-.273.24l-.118.165c-.11.15-.22.262-.377.18a1.226 1.226 0 01-.658-1.204c.048-.495.395-.913.878-1.059a1.262 1.262 0 011.33.394z"></path></svg>
            </a>
            <a href="https://x.com/josepha_mayo" aria-label="X" target="_blank" className="text-text-secondary hover:text-text-primary text-2xl transition-all hover:-translate-y-1">
              <i className="fa-brands fa-x-twitter"></i>
            </a>
            <a href="mailto:ayandajoseph390@gmail.com" aria-label="email Joseph" className="text-text-secondary hover:text-text-primary text-2xl transition-all hover:-translate-y-1">
              <i className="fa-solid fa-envelope"></i>
            </a>
          </div>
          <p className="text-text-secondary text-sm">
            &copy; {new Date().getFullYear()} ayanda joseph. deeper learning.
          </p>
        </div>
      </footer>
    </>
  );
}
