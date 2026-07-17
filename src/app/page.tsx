'use client';

import Image from 'next/image';
import { useState, useEffect } from 'react';
import NeuralNetwork from '@/components/NeuralNetwork';

// Skill Tag component
function SkillTag({ children }: { children: React.ReactNode }) {
  return (
    <span className="skill-tag-hover bg-white/5 px-3 py-2 rounded text-sm text-text-secondary border border-transparent">
      {children}
    </span>
  );
}

// Project Tag component
function Tag({ children }: { children: React.ReactNode }) {
  return (
    <span className="text-xs px-2.5 py-1 bg-white/5 rounded text-text-secondary border border-transparent">
      {children}
    </span>
  );
}

// Skill Card component
function SkillCard({ icon, title, children }: { icon: string; title: string; children: React.ReactNode }) {
  return (
    <div className="card-hover bg-card border border-border-subtle p-8 rounded-2xl">
      <h3 className="mb-6 text-text-primary text-xl flex items-center gap-2 font-display">
        <i className={icon}></i> {title}
      </h3>
      <div className="flex flex-wrap gap-3">
        {children}
      </div>
    </div>
  );
}

// Project Card component
function ProjectCard({
  image,
  title,
  icon,
  description,
  tags,
  links
}: {
  image: string;
  title: string;
  icon: string;
  description: string;
  tags: string[];
  links: { href: string; label: string; icon: string }[];
}) {
  return (
    <article className="card-hover bg-card border border-border-subtle rounded-2xl overflow-hidden flex flex-col">
      <div className="h-[220px] relative overflow-hidden border-b border-border-subtle">
        <Image
          src={image}
          alt={title}
          fill
          sizes="(min-width: 768px) 50vw, 100vw"
          className="img-zoom w-full h-full object-contain object-center bg-card brightness-95"
        />
      </div>
      <div className="p-6 flex flex-col flex-1">
        <div className="flex justify-between items-center mb-2">
          <span className="text-xl font-bold">{title}</span>
          <i className={`${icon} text-accent text-lg`}></i>
        </div>
        <p className="text-sm text-text-secondary mb-4 leading-relaxed flex-1">{description}</p>
        <div className="flex flex-wrap gap-2 mb-4">
          {tags.map((tag, i) => <Tag key={i}>{tag}</Tag>)}
        </div>
        <div className="flex gap-4 pt-4 border-t border-border-subtle">
          {links.map((link, i) => (
            <a
              key={i}
              href={link.href}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm font-semibold text-text-primary hover:text-accent flex items-center gap-1.5 transition-colors"
            >
              <i className={link.icon}></i> {link.label}
            </a>
          ))}
        </div>
      </div>
    </article>
  );
}

// Model/Dataset Card component
function ModelCard({ 
  name, 
  type, 
  description, 
  hfUrl 
}: { 
  name: string; 
  type: 'model' | 'dataset'; 
  description: string; 
  hfUrl: string;
}) {
  const [downloads, setDownloads] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchDownloads = async () => {
      try {
        // Extract repo path correctly based on type
        const repoPath = type === 'dataset'
          ? hfUrl.split('huggingface.co/datasets/')[1]
          : hfUrl.split('huggingface.co/')[1];
        const apiUrl = `https://huggingface.co/api/${type}s/${repoPath}?expand=downloadsAllTime`;
        
        const response = await fetch(apiUrl);
        const data = await response.json();
        
        // Read total all-time downloads from the response
        setDownloads(data.downloadsAllTime || 0);
      } catch (error) {
        console.error('Error fetching downloads:', error);
        setDownloads(null);
      } finally {
        setLoading(false);
      }
    };

    fetchDownloads();
  }, [hfUrl, type]);

  const formatDownloads = (num: number) => {
    if (num >= 1000) {
      return `${(num / 1000).toFixed(2)}k+`;
    }
    return `${num}+`;
  };

  return (
    <div className="bg-card border border-border-subtle rounded-xl p-6 hover:border-accent/50 transition-all">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <i className={`fa-solid ${type === 'model' ? 'fa-brain' : 'fa-database'} text-accent text-xl`}></i>
          <h3 className="text-lg font-bold text-text-primary">{name}</h3>
        </div>
        {!loading && downloads !== null && (
          <span className="text-mono text-[11px] px-2 py-1 bg-white/5 text-text-secondary rounded border border-border-subtle">
            {formatDownloads(downloads)} total downloads
          </span>
        )}
        {loading && (
          <span className="text-xs px-2 py-1 bg-white/5 text-text-secondary rounded animate-pulse">
            loading...
          </span>
        )}
      </div>
      <p className="text-sm text-text-secondary mb-4">{description}</p>
      <a 
        href={hfUrl} 
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-2 text-sm font-medium text-text-secondary hover:text-text-primary transition-colors"
      >
        <svg fill="currentColor" fillRule="evenodd" height="1em" style={{flex:'none',lineHeight:1}} viewBox="0 0 24 24" width="1em" xmlns="http://www.w3.org/2000/svg"><title>HuggingFace</title><path d="M16.781 3.277c2.997 1.704 4.844 4.851 4.844 8.258 0 .995-.155 1.955-.443 2.857a1.332 1.332 0 011.125.4 1.41 1.41 0 01.2 1.723c.204.165.352.385.428.632l.017.062c.06.222.12.69-.2 1.166.244.37.279.836.093 1.236-.255.57-.893 1.018-2.128 1.5l-.202.078-.131.048c-.478.173-.89.295-1.061.345l-.086.024c-.89.243-1.808.375-2.732.394-1.32 0-2.3-.36-2.923-1.067a9.852 9.852 0 01-3.18.018C9.778 21.647 8.802 22 7.494 22a11.249 11.249 0 01-2.541-.343l-.221-.06-.273-.08a16.574 16.574 0 01-1.175-.405c-1.237-.483-1.875-.93-2.13-1.501-.186-.4-.151-.867.093-1.236a1.42 1.42 0 01-.2-1.166c.069-.273.226-.516.447-.694a1.41 1.41 0 01.2-1.722c.233-.248.557-.391.917-.407l.078-.001a9.385 9.385 0 01-.44-2.85c0-3.407 1.847-6.554 4.844-8.258a9.822 9.822 0 019.687 0zM4.188 14.758c.125.687 2.357 2.35 2.14 2.707-.19.315-.796-.239-.948-.386l-.041-.04-.168-.147c-.561-.479-2.304-1.9-2.74-1.432-.43.46.119.859 1.055 1.42l.784.467.136.083c1.045.643 1.12.84.95 1.113-.188.295-3.07-2.1-3.34-1.083-.27 1.011 2.942 1.304 2.744 2.006-.2.7-2.265-1.324-2.685-.537-.425.79 2.913 1.718 2.94 1.725l.16.04.175.042c1.227.284 3.565.65 4.435-.604.673-.973.64-1.709-.248-2.61l-.057-.057c-.945-.928-1.495-2.288-1.495-2.288l-.017-.058-.025-.072c-.082-.22-.284-.639-.63-.584-.46.073-.798 1.21.12 1.933l.05.038c.977.721-.195 1.21-.573.534l-.058-.104-.143-.25c-.463-.799-1.282-2.111-1.739-2.397-.532-.332-.907-.148-.782.541zm14.842-.541c-.533.335-1.563 2.074-1.94 2.751a.613.613 0 01-.687.302.436.436 0 01-.176-.098.303.303 0 01-.049-.06l-.014-.028-.008-.02-.007-.019-.003-.013-.003-.017a.289.289 0 01-.004-.048c0-.12.071-.266.25-.427.026-.024.054-.047.084-.07l.047-.036c.022-.016.043-.032.063-.049.883-.71.573-1.81.131-1.917l-.031-.006-.056-.004a.368.368 0 00-.062.006l-.028.005-.042.014-.039.017-.028.015-.028.019-.036.027-.023.02c-.173.158-.273.428-.31.542l-.016.054s-.53 1.309-1.439 2.234l-.054.054c-.365.358-.596.69-.702 1.018-.143.437-.066.868.21 1.353.055.097.117.195.187.296.882 1.275 3.282.876 4.494.59l.286-.07.25-.074c.276-.084.736-.233 1.2-.42l.188-.077.065-.028.064-.028.124-.056.081-.038c.529-.252.964-.543.994-.827l.001-.036a.299.299 0 00-.037-.139c-.094-.176-.271-.212-.491-.168l-.045.01c-.044.01-.09.024-.136.04l-.097.035-.054.022c-.559.23-1.238.705-1.607.745h.006a.452.452 0 01-.05.003h-.024l-.024-.003-.023-.005c-.068-.016-.116-.06-.14-.142a.22.22 0 01-.005-.1c.062-.345.958-.595 1.713-.91l.066-.028c.528-.224.97-.483.985-.832v-.04a.47.47 0 00-.016-.098c-.048-.18-.175-.251-.36-.251-.785 0-2.55 1.36-2.92 1.36-.025 0-.048-.007-.058-.024a.6.6 0 01-.046-.088c-.1-.238.068-.462 1.06-1.066l.209-.126c.538-.32 1.01-.588 1.341-.831.29-.212.475-.406.503-.6l.003-.028c.008-.113-.038-.227-.147-.344a.266.266 0 00-.07-.054l-.034-.015-.013-.005a.403.403 0 00-.13-.02c-.162 0-.369.07-.595.18-.637.313-1.431.952-1.826 1.285l-.249.215-.033.033c-.08.078-.288.27-.493.386l-.071.037-.041.019a.535.535 0 01-.122.036h.005a.346.346 0 01-.031.003l.01-.001-.013.001c-.079.005-.145-.021-.19-.095a.113.113 0 01-.014-.065c.027-.465 2.034-1.991 2.152-2.642l.009-.048c.1-.65-.271-.817-.791-.493zM11.938 2.984c-4.798 0-8.688 3.829-8.688 8.55 0 .692.083 1.364.24 2.008l.008-.009c.252-.298.612-.46 1.017-.46.355.008.699.117.993.312.22.14.465.384.715.694.261-.372.69-.598 1.15-.605.852 0 1.367.728 1.562 1.383l.047.105.06.127c.192.396.595 1.139 1.143 1.68 1.06 1.04 1.324 2.115.8 3.266a8.865 8.865 0 002.024-.014c-.505-1.12-.26-2.17.74-3.186l.066-.066c.695-.684 1.157-1.69 1.252-1.912.195-.655.708-1.383 1.56-1.383.46.007.889.233 1.15.605.25-.31.495-.553.718-.694a1.87 1.87 0 01.99-.312c.357 0 .682.126.925.36.14-.61.215-1.245.215-1.898 0-4.722-3.89-8.55-8.687-8.55zm1.857 8.926l.439-.212c.553-.264.89-.383.89.152 0 1.093-.771 3.208-3.155 3.262h-.184c-2.325-.052-3.116-2.06-3.156-3.175l-.001-.087c0-1.107 1.452.586 3.25.586.716 0 1.379-.272 1.917-.526zm4.017-3.143c.45 0 .813.358.813.8 0 .441-.364.8-.813.8a.806.806 0 01-.812-.8c0-.442.364-.8.812-.8zm-11.624 0c.448 0 .812.358.812.8 0 .441-.364.8-.812.8a.806.806 0 01-.813-.8c0-.442.364-.8.813-.8zm7.79-.841c.32-.384.846-.54 1.33-.394.483.146.83.564.878 1.06.048.495-.212.97-.659 1.203-.322.168-.447-.477-.767-.585l.002-.003c-.287-.098-.772.362-.925.079a1.215 1.215 0 01.14-1.36zm-4.323 0c.322.384.377.92.14 1.36-.152.283-.64-.177-.925-.079l.003.003c-.108.036-.194.134-.273.24l-.118.165c-.11.15-.22.262-.377.18a1.226 1.226 0 01-.658-1.204c.048-.495.395-.913.878-1.059a1.262 1.262 0 011.33.394z"/></svg>
        HF
      </a>
    </div>
  );
}

export default function Home() {
  const projects = [
    {
      image: "/dr-opic.png",
      title: "DR-OPIC",
      icon: "fa-solid fa-route",
      description: "ML framework for fine-tuning SLMs via Domain-Routed On-Policy Iterative Correction. Combines verified repair, delta-span subtraction, and ZPD-weighted curriculum scheduling. L = L_self + λ_r L_repair + λ_delta L_delta, where w_zpd = 4·p̃·(1−p̃) and p̃ = (s+0.5)/(K+1).",
      tags: ["python", "SLM training", "PyTorch", "verifier"],
      links: [
        { href: "/dr-opic", label: "see more", icon: "fa-solid fa-arrow-right" },
        { href: "https://github.com/josepha-mayo/DR-OPIC", label: "source", icon: "fa-brands fa-github" }
      ]
    },
    {
      image: "/vector_projection.png",
      title: "Model Unfetter",
      icon: "fa-solid fa-unlock",
      description: "Directional ablation engine for LLM unalignment. Projects and removes refusal directions from model weights while maintaining capabilities.",
      tags: ["python", "red teaming", "research"],
      links: [
        { href: "/model-ablation", label: "see more", icon: "fa-solid fa-arrow-right" },
        { href: "https://github.com/josepha-mayo/model-unfetter", label: "source", icon: "fa-brands fa-github" }
      ]
    },
    {
      image: "/swarms.png",
      title: "SWARMs Debate Primitive",
      icon: "fa-solid fa-network-wired",
      description: "Multi-agent debate and vote coordination system on Solana blockchain. Agents assume distinct personas to debate complex questions, with full session transcripts hashed and recorded on-chain for verifiable AI consensus.",
      tags: ["Python", "Solana", "multi-agent", "blockchain"],
      links: [
        { href: "https://github.com/josepha-mayo/Swarms", label: "source", icon: "fa-brands fa-github" }
      ]
    },
    {
      image: "/intellectsafe.png",
      title: "IntellectSafe",
      icon: "fa-solid fa-lock",
      description: "AI engine with multi-model LLM Council, Universal Proxy for frontier models, deepfake detection, and adversarial defense suite.",
      tags: ["fastAPI", "next.js", "security"],
      links: [
        { href: "https://intellect-safe.vercel.app", label: "live demo", icon: "fa-solid fa-arrow-up-right-from-square" },
        { href: "https://github.com/josepha-mayo/IntellectSafe", label: "source", icon: "fa-brands fa-github" }
      ]
    },
    {
      image: "/modelfang.png",
      title: "ModelFang",
      icon: "fa-solid fa-mask",
      description: "Graph-based adversarial testing framework for LLMs with multi-turn jailbreak attacks, FSM evaluator, and real-time analyst dashboard.",
      tags: ["python", "next.js", "red teaming"],
      links: [
        { href: "https://model-fang.vercel.app", label: "live demo", icon: "fa-solid fa-arrow-up-right-from-square" },
        { href: "https://github.com/josepha-mayo/ModelFang", label: "source", icon: "fa-brands fa-github" }
      ]
    },
    {
      image: "/mayo_flowchart.png",
      title: "Mayo",
      icon: "fa-solid fa-robot",
      description: "Autonomous triple-AI engine that analyzes codebases and opens validated PRs hourly with cross-repo global memory.",
      tags: ["python", "agentic AI", "GitHub"],
      links: [
        { href: "https://github.com/josepha-mayo/mayo", label: "source", icon: "fa-brands fa-github" }
      ]
    }
  ];

  return (
    <>
      {/* Navigation */}
      <nav className="fixed top-0 w-full h-[70px] nav-glass border-b border-border-subtle z-50 flex items-center" aria-label="primary">
        <div className="container mx-auto px-8 flex justify-between items-center">
          <a href="#" className="font-display text-2xl font-bold text-text-primary">
            AJ<span className="text-accent">.</span>
          </a>

          <ul className="hidden md:flex items-center gap-8 list-none">
            <li><a href="#about" className="text-text-secondary hover:text-text-primary text-[15px] font-medium transition-colors">about</a></li>
            <li><a href="#skills" className="text-text-secondary hover:text-text-primary text-[15px] font-medium transition-colors">tech stack</a></li>
            <li><a href="#work" className="text-text-secondary hover:text-text-primary text-[15px] font-medium transition-colors">work</a></li>
            <li><a href="#contact" className="text-text-secondary hover:text-text-primary text-[15px] font-medium transition-colors">contact</a></li>
            <div className="flex gap-4 ml-4 pl-4 border-l border-border-subtle">
              <a href="https://github.com/josepha-mayo" target="_blank" className="text-text-secondary hover:text-text-primary text-lg transition-colors">
                <i className="fa-brands fa-github"></i>
              </a>
              <a href="https://huggingface.co/josephmayo" target="_blank" className="text-text-secondary hover:text-text-primary text-lg transition-colors flex items-center justify-center" title="HuggingFace">
                <svg fill="currentColor" fill-rule="evenodd" height="1em" style={{flex:'none',lineHeight:1}} viewBox="0 0 24 24" width="1em" xmlns="http://www.w3.org/2000/svg"><title>HuggingFace</title><path d="M16.781 3.277c2.997 1.704 4.844 4.851 4.844 8.258 0 .995-.155 1.955-.443 2.857a1.332 1.332 0 011.125.4 1.41 1.41 0 01.2 1.723c.204.165.352.385.428.632l.017.062c.06.222.12.69-.2 1.166.244.37.279.836.093 1.236-.255.57-.893 1.018-2.128 1.5l-.202.078-.131.048c-.478.173-.89.295-1.061.345l-.086.024c-.89.243-1.808.375-2.732.394-1.32 0-2.3-.36-2.923-1.067a9.852 9.852 0 01-3.18.018C9.778 21.647 8.802 22 7.494 22a11.249 11.249 0 01-2.541-.343l-.221-.06-.273-.08a16.574 16.574 0 01-1.175-.405c-1.237-.483-1.875-.93-2.13-1.501-.186-.4-.151-.867.093-1.236a1.42 1.42 0 01-.2-1.166c.069-.273.226-.516.447-.694a1.41 1.41 0 01.2-1.722c.233-.248.557-.391.917-.407l.078-.001a9.385 9.385 0 01-.44-2.85c0-3.407 1.847-6.554 4.844-8.258a9.822 9.822 0 019.687 0zM4.188 14.758c.125.687 2.357 2.35 2.14 2.707-.19.315-.796-.239-.948-.386l-.041-.04-.168-.147c-.561-.479-2.304-1.9-2.74-1.432-.43.46.119.859 1.055 1.42l.784.467.136.083c1.045.643 1.12.84.95 1.113-.188.295-3.07-2.1-3.34-1.083-.27 1.011 2.942 1.304 2.744 2.006-.2
                .7-2.265-1.324-2.685-.537-.425.79 2.913 1.718 2.94 1.725l.16.04.175.042c1.227.284 3.565.65 4.435-.604.673-.973.64-1.709-.248-2.61l-.057-.057c-.945-.928-1.495-2.288-1.495-2.288l-.017-.058-.025-.072c-.082-.22-.284-.639-.63-.584-.46.073-.798 1.21.12 1.933l.05.038c.977.721-.195 1.21-.573.534l-.058-.104-.143-.25c-.463-.799-1.282-2.111-1.739-2.397-.532-.332-.907-.148-.782.541zm14.842-.541c-.533.335-1.563 2.074-1.94 2.751a.613.613 0 01-.687.302.436.436 0 01-.176-.098.303.303 0 01-.049-.06l-.014-.028-.008-.02-.007-.019-.003-.013-.003-.017a.289.289 0 01-.004-.048c0-.12.071-.266.25-.427.026-.024.054-.047.084-.07l.047-.036c.022-.016.043-.032.063-.049.883-.71.573-1.81.131-1.917l-.031-.006-.056-.004a.368.368 0 00-.062.006l-.028.005-.042.014-.039.017-.028.015-.028.019-.036.027-.023.02c-.173.158-.273.428-.31.542l-.016.054s-.53 1.309-1.439 2.234l-.054.054c-.365.358-.596.69-.702 1.018-.143.437-.066.868.21 1.353.055.097.117.195.187.296.882 1.275 3.282.876 4.494.59l.286-.07.25-.074c.276-.084.736-.233 1.2-.42l.188-.077.065-.028.064-.028.124-.056.081-.038c.529-.252.964-.543.994-.827l.001-.036a.299.299 0 00-.037-.139c-.094-.176-.271-.212-.491-.168l-.045.01c-.044.01-.09.024-.136.04l-.097.035-.054.022c-.559.23-1.238.705-1.607.745h.006a.452.452 0 01-.05.003h-.024l-.024-.003-.023-.005c-.068-.016-.116-.06-.14-.142a.22.22 0 01-.005-.1c.062-.345.958-.595 1.713-.91l.066-.028c.528-.224.97-.483.985-.832v-.04a.47.47 0 00-.016-.098c-.048-.18-.175-.251-.36-.251-.785 0-2.55 1.36-2.92 1.36-.025 0-.048-.007-.058-.024a.6.6 0 01-.046-.088c-.1-.238.068-.462 1.06-1.066l.209-.126c.538-.32 1.01-.588 1.341-.831.29-.212.475-.406.503-.6l.003-.028c.008-.113-.038-.227-.147-.344a.266.266 0 00-.07-.054l-.034-.015-.013-.005a.403.403 0 00-.13-.02c-.162 0-.369.07-.595.18-.637.313-1.431.952-1.826 1.285l-.249.215-.033.033c-.08.078-.288.27-.493.386l-.071.037-.041.019a.535.535 0 01-.122.036h.005a.346.346 0 01-.031.003l.01-.001-.013.001c-.079.005-.145-.021-.19-.095a.113.113 0 01-.014-.065c.027-.465 2.034-1.991 2.152-2.642l.009-.048c.1-.65-.271-.817-.791-.493zM11.938 2.984c-4.798 0-8.688 3.829-8.688 8.55 0 .692.083 1.364.24 2.008l.008-.009c.252-.298.612-.46 1.017-.46.355.008.699.117.993.312.22.14.465.384.715.694.261-.372.69-.598 1.15-.605.852 0 1.367.728 1.562 1.383l.047.105.06.127c.192.396.595 1.139 1.143 1.68 1.06 1.04 1.324 2.115.8 3.266a8.865 8.865 0 002.024-.014c-.505-1.12-.26-2.17.74-3.186l.066-.066c.695-.684 1.157-1.69 1.252-1.912.195-.655.708-1.383 1.56-1.383.46.007.889.233 1.15.605.25-.31.495-.553.718-.694a1.87 1.87 0 01.99-.312c.357 0 .682.126.925.36.14-.61.215-1.245.215-1.898 0-4.722-3.89-8.55-8.687-8.55zm1.857 8.926l.439-.212c.553-.264.89-.383.89.152 0 1.093-.771 3.208-3.155 3.262h-.184c-2.325-.052-3.116-2.06-3.156-3.175l-.001-.087c0-1.107 1.452.586 3.25.586.716 0 1.379-.272 1.917-.526zm4.017-3.143c.45 0 .813.358.813.8 0 .441-.364.8-.813.8a.806.806 0 01-.812-.8c0-.442.364-.8.812-.8zm-11.624 0c.448 0 .812.358.812.8 0 .441-.364.8-.812.8a.806.806 0 01-.813-.8c0-.442.364-.8.813-.8zm7.79-.841c.32-.384.846-.54 1.33-.394.483.146.83.564.878 1.06.048.495-.212.97-.659 1.203-.322.168-.447-.477-.767-.585l.002-.003c-.287-.098-.772.362-.925.079a1.215 1.215 0 01.14-1.36zm-4.323 0c.322.384.377.92.14 1.36-.152.283-.64-.177-.925-.079l.003.003c-.108.036-.194.134-.273.24l-.118.165c-.11.15-.22.262-.377.18a1.226 1.226 0 01-.658-1.204c.048-.495.395-.913.878-1.059a1.262 1.262 0 011.33.394z"></path></svg>
              </a>
              <a href="https://x.com/josepha_mayo" target="_blank" className="text-text-secondary hover:text-text-primary text-lg transition-colors">
                <i className="fa-brands fa-x-twitter"></i>
              </a>
              <a href="mailto:ayandajoseph390@gmail.com" className="text-text-secondary hover:text-text-primary text-lg transition-colors">
                <i className="fa-solid fa-envelope"></i>
              </a>
              <a href="https://wa.me/2349019029665" target="_blank" className="text-text-secondary hover:text-text-primary text-lg transition-colors">
                <i className="fa-brands fa-whatsapp"></i>
              </a>
            </div>
          </ul>

          <button className="md:hidden text-text-primary text-2xl bg-transparent border-none cursor-pointer">
            <i className="fa-solid fa-bars"></i>
          </button>
        </div>
      </nav>

      <main id="main">
      {/* Hero Section */}
      <header
        className="min-h-[100dvh] flex items-end pt-[100px] pb-16 relative overflow-hidden hero-grain"
        style={{
          background: 'linear-gradient(to bottom, rgba(10,10,10,0.78), rgba(10,10,10,0.95)), url(/image.jpg)',
          backgroundSize: 'cover',
          backgroundPosition: 'center'
        }}
      >
        <div className="container mx-auto px-8 max-w-6xl z-10">
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
              <NeuralNetwork />
            </div>
          </div>
        </div>
      </header>

      {/* About Section */}
      <section id="about" className="py-32 md:py-40">
        <div className="container mx-auto px-8 max-w-6xl">
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
                research that ships. evaluations that don&apos;t lie. tools other engineers actually use.
              </p>
            </div>

            <div className="mission-card rounded-2xl p-8 min-h-[520px] border border-border-subtle relative overflow-hidden bg-card">
              <div className="absolute inset-0 bg-cover bg-no-repeat bg-center mission-card-bg" style={{ backgroundImage: 'url(/joseph.jpg)', filter: 'brightness(0.9) contrast(1.1)', backgroundPosition: 'center 0%' }} />
              <div className="absolute inset-0 bg-black/50 mission-card-overlay" />
              <div className="relative z-10 mission-card-content">
                <h3 className="mb-6 text-text-primary text-xl">
                  <i className="fa-solid fa-bullseye text-accent mr-2"></i> core mission
                </h3>
                <ul className="list-none flex flex-col gap-4 text-text-secondary">
                  <li><i className="fa-solid fa-check text-accent mr-2"></i> ML engineering & research</li>
                  <li><i className="fa-solid fa-check text-accent mr-2"></i> red teaming & adversarial testing</li>
                  <li><i className="fa-solid fa-check text-accent mr-2"></i> agentic systems</li>
                  <li><i className="fa-solid fa-check text-accent mr-2"></i> dataset curation & synthetic data</li>
                  <li><i className="fa-solid fa-check text-accent mr-2"></i> local AI</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Tech Stack Section */}
      <section id="skills" className="py-24">
        <div className="container mx-auto px-8">
          <h2 className="text-4xl mb-16 text-center font-display">tech arsenal</h2>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            <SkillCard icon="fa-solid fa-weight-hanging" title="model optimization &amp; deployment">
              <SkillTag>LoRA / QLoRA</SkillTag>
              <SkillTag>fine-tuning</SkillTag>
              <SkillTag>DPO</SkillTag>
              <SkillTag>ORPO</SkillTag>
              <SkillTag>quantization (GGUF)</SkillTag>
            </SkillCard>

            <SkillCard icon="fa-solid fa-mask" title="red teaming &amp; adversarial testing">
              <SkillTag>refusal ablation</SkillTag>
              <SkillTag>jailbreak research</SkillTag>
              <SkillTag>adversarial testing</SkillTag>
              <SkillTag>compliance pairs</SkillTag>
            </SkillCard>

            <SkillCard icon="fa-solid fa-microchip" title="systems &amp; core">
              <SkillTag>C</SkillTag>
              <SkillTag>holy C</SkillTag>
              <SkillTag>python</SkillTag>
              <SkillTag>typeScript</SkillTag>
            </SkillCard>

            <SkillCard icon="fa-solid fa-server" title="backend">
              <SkillTag>fastAPI</SkillTag>
              <SkillTag>node.js</SkillTag>
              <SkillTag>express</SkillTag>
              <SkillTag>django</SkillTag>
              <SkillTag>flask</SkillTag>
            </SkillCard>

            <SkillCard icon="fa-solid fa-database" title="databases">
              <SkillTag>postgreSQL</SkillTag>
              <SkillTag>sqlite</SkillTag>
              <SkillTag>redis</SkillTag>
              <SkillTag>neon db</SkillTag>
            </SkillCard>

            <SkillCard icon="fa-solid fa-toolbox" title="tools &amp; cloud">
              <SkillTag>prime intellect</SkillTag>
              <SkillTag>cloudflare</SkillTag>
              <SkillTag>backblaze</SkillTag>
              <SkillTag>github</SkillTag>
              <SkillTag>rest APIs</SkillTag>
              <SkillTag>docker</SkillTag>
            </SkillCard>

            <SkillCard icon="fa-solid fa-brain" title="ML &amp; deep learning">
              <SkillTag>PyTorch</SkillTag>
              <SkillTag>transformers</SkillTag>
              <SkillTag>hugging face</SkillTag>
              <SkillTag>model training</SkillTag>
              <SkillTag>fine-tuning</SkillTag>
              <SkillTag>too many to mention</SkillTag>
            </SkillCard>

            <SkillCard icon="fa-solid fa-flask" title="data engineering">
              <SkillTag>dataset curation</SkillTag>
              <SkillTag>synthetic data generation</SkillTag>
              <SkillTag>data preprocessing</SkillTag>
              <SkillTag>quality filtering</SkillTag>
              <SkillTag>deduplication</SkillTag>
            </SkillCard>

            <SkillCard icon="fa-solid fa-crosshairs" title="current focus">
              <SkillTag>ML engineering</SkillTag>
              <SkillTag>red teaming</SkillTag>
              <SkillTag>agentic systems</SkillTag>
              <SkillTag>model evaluation</SkillTag>
            </SkillCard>
          </div>
        </div>
      </section>

      {/* Projects Section */}
      <section id="work" className="py-24">
        <div className="container mx-auto px-8">
          <h2 className="text-4xl mb-16 text-center font-display">selected projects</h2>

          <div className="grid md:grid-cols-2 gap-10">
            {projects.map((project, index) => (
              <ProjectCard key={index} {...project} />
            ))}
          </div>

          <div className="flex justify-center mt-12 mb-4">
            <a
              href="https://github.com/josepha-mayo?tab=repositories"
              target="_blank"
              className="w-full max-w-[250px] p-4 bg-gradient-to-br from-[#111] to-[#0a0a0a] border border-[#333] rounded-xl flex items-center justify-center gap-3 transition-all no-underline hover:border-[#555]"
            >
              <i className="fa-brands fa-github text-white text-lg"></i>
              <span className="text-[#ccc] font-display text-[15px] font-medium">View All Projects</span>
              <i className="fa-solid fa-arrow-right text-accent text-sm"></i>
            </a>
          </div>
        </div>
      </section>

      {/* Models & Datasets Section */}
      <section id="models" className="py-32 md:py-40 bg-background">
        <div className="container mx-auto px-8 max-w-6xl">
          <div className="flex items-baseline justify-between gap-4 mb-16">
            <h2 className="text-3xl md:text-4xl font-display font-semibold tracking-tight">models &amp; datasets</h2>
            <a href="https://huggingface.co/josephmayo" target="_blank" rel="noopener noreferrer" className="text-mono text-xs text-text-secondary hover:text-text-primary transition-colors">huggingface.co/josephmayo &rarr;</a>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            <ModelCard
              name="ZAYA1-8B-Coder-GGUF"
              type="model"
              description="quantized gguf builds of ZAYA1-8B-Coder for local inference via llama.cpp, ollama, and lm studio."
              hfUrl="https://huggingface.co/josephmayo/ZAYA1-8B-Coder-GGUF"
            />

            <ModelCard
              name="gemma-4-E4B-it-Coder-GGUF"
              type="model"
              description="quantized gguf builds of gemma-4-E4B-it-Coder for local inference via llama.cpp, ollama and lm studio."
              hfUrl="https://huggingface.co/josephmayo/gemma-4-E4B-it-Coder-GGUF"
            />

            <ModelCard
              name="Holo-3.1-9B-Coder"
              type="model"
              description="fine-tuned Hcompany Holo-3.1-9B for coding tasks. merged model optimized for python and software development."
              hfUrl="https://huggingface.co/josephmayo/Holo-3.1-9B-Coder"
            />

            <ModelCard
              name="Holo-3.1-4B-Coder-GGUF"
              type="model"
              description="quantized gguf builds of Holo-3.1-4B-Coder for local inference via llama.cpp, ollama and lm studio."
              hfUrl="https://huggingface.co/josephmayo/Holo-3.1-4B-Coder-GGUF"
            />

            <ModelCard
              name="Qwopus 9B Unfettered GGUF"
              type="model"
              description="quantized gguf version of qwopus 9b unfettered for efficient local inference. 100% compliance on harmful evals."
              hfUrl="https://huggingface.co/josephmayo/Qwopus-9B-Unfettered-GGUF"
            />

            <ModelCard
              name="Fara-7B-Abliterated-v2-GGUF"
              type="model"
              description="quantized gguf builds of Fara-7B-Abliterated-v2 for local inference via llama.cpp, ollama, and lm studio."
              hfUrl="https://huggingface.co/josephmayo/Fara-7B-Abliterated-v2-GGUF"
            />

            <ModelCard
              name="Qwen2.5-0.5B-Unfettered"
              type="model"
              description="surgical unalignment of Qwen 0.5B Instruct optimized for low-end hardware. 100% compliance, zero refusal. runs on 1GB RAM."
              hfUrl="https://huggingface.co/josephmayo/Qwen2.5-0.5B-Unfettered"
            />

            <ModelCard
              name="Curated OpenBMB Code/Math"
              type="dataset"
              description="31,909 rows of curated code/math post-training data derived from OpenBMB UltraData. includes SFT and think splits."
              hfUrl="https://huggingface.co/datasets/josephmayo/curated-openbmb-code-math"
            />

            <ModelCard
              name="Qwopus 9B Unfettered"
              type="model"
              description="9B uncensored language model. directional ablation applied to remove refusal mechanisms. 100% compliance on harmful evals."
              hfUrl="https://huggingface.co/josephmayo/Qwopus-9B-Unfettered"
            />

            <ModelCard
              name="Holo-3.1-4B-Coder"
              type="model"
              description="fine-tuned Hcompany Holo-3.1-4B for coding tasks. merged model optimized for python and software development."
              hfUrl="https://huggingface.co/josephmayo/Holo-3.1-4B-Coder"
            />

            <ModelCard
              name="gemma-4-E4B-it-Coder"
              type="model"
              description="fine-tuned google gemma-4-E4B-it for coding tasks. multimodal model optimized for code generation."
              hfUrl="https://huggingface.co/josephmayo/gemma-4-E4B-it-Coder"
            />

            <ModelCard
              name="Public Curated Coding Data"
              type="dataset"
              description="mixed-origin public coding data with 2,700+ prompt/response pairs for llm training experiments."
              hfUrl="https://huggingface.co/datasets/josephmayo/public-curated-coding-data"
            />

            <ModelCard
              name="Fara-7B-Abliterated-v2"
              type="model"
              description="refusal-direction-orthogonalized variant of microsoft/Fara-7B. 98.75% compliance on held-out harmful evals."
              hfUrl="https://huggingface.co/josephmayo/Fara-7B-Abliterated-v2"
            />

            <ModelCard
              name="ZAYA1-8B-Coder"
              type="model"
              description="merged coder model from Zyphra/ZAYA1-8B plus custom lora. +24% lift on python code evaluation gate."
              hfUrl="https://huggingface.co/josephmayo/ZAYA1-8B-Coder"
            />

            <ModelCard
              name="Refusal Compliance Pairs"
              type="dataset"
              description="200+ curated refusal-compliance prompt pairs for red teaming and adversarial evaluation."
              hfUrl="https://huggingface.co/datasets/josephmayo/refusal-compliance-pairs"
            />

            <ModelCard
              name="gemma-4-E4B-it-coding-lora"
              type="model"
              description="lora adapter for google gemma-4-E4B-it focused on code generation and software development tasks."
              hfUrl="https://huggingface.co/josephmayo/gemma-4-E4B-it-coding-lora"
            />

            <ModelCard
              name="Holo-3.1-4B-Coder-LoRA"
              type="model"
              description="lora/qlora adapter for Holo-3.1-4B focused on coding and python development."
              hfUrl="https://huggingface.co/josephmayo/Holo-3.1-4B-Coder-LoRA"
            />

            <ModelCard
              name="ZAYA1-8B-Coder-LoRA"
              type="model"
              description="lora adapter for Zyphra/ZAYA1-8B focused on python code generation. +101% relative lift over base."
              hfUrl="https://huggingface.co/josephmayo/ZAYA1-8B-Coder-LoRA"
            />

            <ModelCard
              name="Mellum2-12B-A2.5B-Thinking-Abliterated-GGUF"
              type="model"
              description="quantized gguf builds of Mellum2-12B ablated for refusal removal. MoE architecture with per-expert per-layer projected ablation."
              hfUrl="https://huggingface.co/josephmayo/Mellum2-12B-A2.5B-Thinking-Abliterated-GGUF"
            />

            <ModelCard
              name="Mellum2-12B-A2.5B-Thinking-Abliterated"
              type="model"
              description="abliterated Mellum2-12B thinking model from JetBrains. refusal-direction orthogonalized with CoT steering for reasoning tasks."
              hfUrl="https://huggingface.co/josephmayo/Mellum2-12B-A2.5B-Thinking-Abliterated"
            />

            <ModelCard
              name="LFM2.5-8B-A1B-Coder-GGUF"
              type="model"
              description="quantized gguf builds of LFM2.5-8B-A1B Coder for local inference via llama.cpp, ollama and lm studio."
              hfUrl="https://huggingface.co/josephmayo/LFM2.5-8B-A1B-Coder-GGUF"
            />

            <ModelCard
              name="LFM2.5-8B-A1B-Coder"
              type="model"
              description="fine-tuned LiquidAI LFM2.5-8B-A1B MoE model for real-world coding tasks. multilingual and conversation-optimized."
              hfUrl="https://huggingface.co/josephmayo/LFM2.5-8B-A1B-Coder"
            />

            <ModelCard
              name="LFM2.5-8B-A1B-Coder-LoRA"
              type="model"
              description="lightweight lora adapter for LFM2.5-8B-A1B focused on real-world coding and multilingual tasks."
              hfUrl="https://huggingface.co/josephmayo/LFM2.5-8B-A1B-Coder-LoRA"
            />

            <ModelCard
              name="HRM-Text-1B-sft-code"
              type="model"
              description="fine-tuned sapientinc HRM-Text-1B for code generation. trained on HumanEval and MBPP benchmarks."
              hfUrl="https://huggingface.co/josephmayo/HRM-Text-1B-sft-code"
            />

            <ModelCard
              name="HRM-Text-1B-sft-code-LoRA"
              type="model"
              description="lora adapter for HRM-Text-1B focused on python code generation and coding benchmarks."
              hfUrl="https://huggingface.co/josephmayo/HRM-Text-1B-sft-code-LoRA"
            />

            <ModelCard
              name="Qwen2.5-agentic-7B-SLM-LoRA"
              type="model"
              description="lora adapter for Qwen2.5-7B optimized for agentic tasks and tool-use workflows."
              hfUrl="https://huggingface.co/josephmayo/Qwen2.5-agentic-7B-SLM-LoRA"
            />

            <ModelCard
              name="Qwen2.5-Coder-3B-Cheat-Control-LoRA-Experiment"
              type="model"
              description="experimental lora adapter for Qwen2.5-Coder-3B exploring cheat/control dynamics in small language models."
              hfUrl="https://huggingface.co/josephmayo/Qwen2.5-Coder-3B-Cheat-Control-LoRA-Experiment"
            />

            <ModelCard
              name="Qwen2.5-Coder-3B-Clean-LoRA-Experiment"
              type="model"
              description="experimental lora adapter for Qwen2.5-Coder-3B exploring clean baseline dynamics in small language models."
              hfUrl="https://huggingface.co/josephmayo/Qwen2.5-Coder-3B-Clean-LoRA-Experiment"
            />
          </div>
        </div>
      </section>

      </main>

      {/* Footer */}
      <footer id="contact" className="bg-card border-t border-border-subtle py-16 text-center">
        <div className="container mx-auto px-8">
          <h2 className="mb-8 text-3xl">let&apos;s build something impactful & innovative</h2>
          <div className="flex justify-center gap-8 mb-8">
            <a href="https://github.com/josepha-mayo" target="_blank" className="text-text-secondary hover:text-text-primary text-2xl transition-all hover:-translate-y-1">
              <i className="fa-brands fa-github"></i>
            </a>
            <a href="https://huggingface.co/josephmayo" target="_blank" className="text-text-secondary hover:text-text-primary text-2xl transition-all hover:-translate-y-1 flex items-center justify-center" title="HuggingFace">
              <svg fill="currentColor" fillRule="evenodd" height="1em" style={{flex:'none',lineHeight:1}} viewBox="0 0 24 24" width="1em" xmlns="http://www.w3.org/2000/svg"><title>HuggingFace</title><path d="M16.781 3.277c2.997 1.704 4.844 4.851 4.844 8.258 0 .995-.155 1.955-.443 2.857a1.332 1.332 0 011.125.4 1.41 1.41 0 01.2 1.723c.204.165.352.385.428.632l.017.062c.06.222.12.69-.2 1.166.244.37.279.836.093 1.236-.255.57-.893 1.018-2.128 1.5l-.202.078-.131.048c-.478.173-.89.295-1.061.345l-.086.024c-.89.243-1.808.375-2.732.394-1.32 0-2.3-.36-2.923-1.067a9.852 9.852 0 01-3.18.018C9.778 21.647 8.802 22 7.494 22a11.249 11.249 0 01-2.541-.343l-.221-.06-.273-.08a16.574 16.574 0 01-1.175-.405c-1.237-.483-1.875-.93-2.13-1.501-.186-.4-.151-.867.093-1.236a1.42 1.42 0 01-.2-1.166c.069-.273.226-.516.447-.694a1.41 1.41 0 01.2-1.722c.233-.248.557-.391.917-.407l.078-.001a9.385 9.385 0 01-.44-2.85c0-3.407 1.847-6.554 4.844-8.258a9.822 9.822 0 019.687 0zM4.188 14.758c.125.687 2.357 2.35 2.14 2.707-.19.315-.796-.239-.948-.386l-.041-.04-.168-.147c-.561-.479-2.304-1.9-2.74-1.432-.43.46.119.859 1.055 1.42l.784.467.136.083c1.045.643 1.12.84.95 1.113-.188.295-3.07-2.1-3.34-1.083-.27 1.011 2.942 1.304 2.744 2.006-.2.7-2.265-1.324-2.685-.537-.425.79 2.913 1.718 2.94 1.725l.16.04.175.042c1.227.284 3.565.65 4.435-.604.673-.973.64-1.709-.248-2.61l-.057-.057c-.945-.928-1.495-2.288-1.495-2.288l-.017-.058-.025-.072c-.082-.22-.284-.639-.63-.584-.46.073-.798 1.21.12 1.933l.05.038c.977.721-.195 1.21-.573.534l-.058-.104-.143-.25c-.463-.799-1.282-2.111-1.739-2.397-.532-.332-.907-.148-.782.541zm14.842-.541c-.533.335-1.563 2.074-1.94 2.751a.613.613 0 01-.687.302.436.436 0 01-.176-.098.303.303 0 01-.049-.06l-.014-.028-.008-.02-.007-.019-.003-.013-.003-.017a.289.289 0 01-.004-.048c0-.12.071-.266.25-.427.026-.024.054-.047.084-.07l.047-.036c.022-.016.043-.032.063-.049.883-.71.573-1.81.131-1.917l-.031-.006-.056-.004a.368.368 0 00-.062.006l-.028.005-.042.014-.039.017-.028.015-.028.019-.036.027-.023.02c-.173.158-.273.428-.31.542l-.016.054s-.53 1.309-1.439 2.234l-.054.054c-.365.358-.596.69-.702 1.018-.143.437-.066.868.21 1.353.055.097.117.195.187.296.882 1.275 3.282.876 4.494.59l.286-.07.25-.074c.276-.084.736-.233 1.2-.42l.188-.077.065-.028.064-.028.124-.056.081-.038c.529-.252.964-.543.994-.827l.001-.036a.299.299 0 00-.037-.139c-.094-.176-.271-.212-.491-.168l-.045.01c-.044.01-.09.024-.136.04l-.097.035-.054.022c-.559.23-1.238.705-1.607.745h.006a.452.452 0 01-.05.003h-.024l-.024-.003-.023-.005c-.068-.016-.116-.06-.14-.142a.22.22 0 01-.005-.1c.062-.345.958-.595 1.713-.91l.066-.028c.528-.224.97-.483.985-.832v-.04a.47.47 0 00-.016-.098c-.048-.18-.175-.251-.36-.251-.785 0-2.55 1.36-2.92 1.36-.025 0-.048-.007-.058-.024a.6.6 0 01-.046-.088c-.1-.238.068-.462 1.06-1.066l.209-.126c.538-.32 1.01-.588 1.341-.831.29-.212.475-.406.503-.6l.003-.028c.008-.113-.038-.227-.147-.344a.266.266 0 00-.07-.054l-.034-.015-.013-.005a.403.403 0 00-.13-.02c-.162 0-.369.07-.595.18-.637.313-1.431.952-1.826 1.285l-.249.215-.033.033c-.08.078-.288.27-.493.386l-.071.037-.041.019a.535.535 0 01-.122.036h.005a.346.346 0 01-.031.003l.01-.001-.013.001c-.079.005-.145-.021-.19-.095a.113.113 0 01-.014-.065c.027-.465 2.034-1.991 2.152-2.642l.009-.048c.1-.65-.271-.817-.791-.493zM11.938 2.984c-4.798 0-8.688 3.829-8.688 8.55 0 .692.083 1.364.24 2.008l.008-.009c.252-.298.612-.46 1.017-.46.355.008.699.117.993.312.22.14.465.384.715.694.261-.372.69-.598 1.15-.605.852 0 1.367.728 1.562 1.383l.047.105.06.127c.192.396.595 1.139 1.143 1.68 1.06 1.04 1.324 2.115.8 3.266a8.865 8.865 0 002.024-.014c-.505-1.12-.26-2.17.74-3.186l.066-.066c.695-.684 1.157-1.69 1.252-1.912.195-.655.708-1.383 1.56-1.383.46.007.889.233 1.15.605.25-.31.495-.553.718-.694a1.87 1.87 0 01.99-.312c.357 0 .682.126.925.36.14-.61.215-1.245.215-1.898 0-4.722-3.89-8.55-8.687-8.55zm1.857 8.926l.439-.212c.553-.264.89-.383.89.152 0 1.093-.771 3.208-3.155 3.262h-.184c-2.325-.052-3.116-2.06-3.156-3.175l-.001-.087c0-1.107 1.452.586 3.25.586.716 0 1.379-.272 1.917-.526zm4.017-3.143c.45 0 .813.358.813.8 0 .441-.364.8-.813.8a.806.806 0 01-.812-.8c0-.442.364-.8.812-.8zm-11.624 0c.448 0 .812.358.812.8 0 .441-.364.8-.812.8a.806.806 0 01-.813-.8c0-.442.364-.8.813-.8zm7.79-.841c.32-.384.846-.54 1.33-.394.483.146.83.564.878 1.06.048.495-.212.97-.659 1.203-.322.168-.447-.477-.767-.585l.002-.003c-.287-.098-.772.362-.925.079a1.215 1.215 0 01.14-1.36zm-4.323 0c.322.384.377.92.14 1.36-.152.283-.64-.177-.925-.079l.003.003c-.108.036-.194.134-.273.24l-.118.165c-.11.15-.22.262-.377.18a1.226 1.226 0 01-.658-1.204c.048-.495.395-.913.878-1.059a1.262 1.262 0 011.33.394z"></path></svg>
            </a>
            <a href="https://x.com/josepha_mayo" target="_blank" className="text-text-secondary hover:text-text-primary text-2xl transition-all hover:-translate-y-1">
              <i className="fa-brands fa-x-twitter"></i>
            </a>
            <a href="mailto:ayandajoseph390@gmail.com" className="text-text-secondary hover:text-text-primary text-2xl transition-all hover:-translate-y-1">
              <i className="fa-solid fa-envelope"></i>
            </a>
            <a href="https://wa.me/2349019029665" target="_blank" className="text-text-secondary hover:text-text-primary text-2xl transition-all hover:-translate-y-1">
              <i className="fa-brands fa-whatsapp"></i>
            </a>
          </div>
          <div className="flex justify-center mb-8">
            <a
              href="/opensource-donations"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg font-medium text-sm bg-white/5 border border-border-subtle text-text-secondary hover:text-text-primary hover:border-accent/50 transition-all"
            >
              <i className="fa-solid fa-heart text-accent"></i>
              support open source
            </a>
          </div>
          <p className="text-text-secondary text-sm">
            &copy; {new Date().getFullYear()} ayanda joseph. building impactful things.
          </p>
        </div>
      </footer>
    </>
  );
}
