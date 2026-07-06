"use client";

import Link from "next/link";
import { useState } from "react";

export const metadata = {
  title: "Support Open Source — Ayanda Joseph",
  description: "Support open source AI/ML research. Every contribution helps build better tools for the community.",
};

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <button
      onClick={handleCopy}
      className="text-xs px-3 py-1.5 bg-white/5 hover:bg-white/10 border border-border-subtle rounded-md text-text-secondary hover:text-text-primary transition-all font-[family-name:var(--font-geist-mono)]"
    >
      {copied ? (
        <span className="flex items-center gap-1.5">
          <i className="fa-solid fa-check text-accent"></i> copied
        </span>
      ) : (
        <span className="flex items-center gap-1.5">
          <i className="fa-regular fa-copy"></i> copy
        </span>
      )}
    </button>
  );
}

export default function OpenSourceDonationsPage() {
  const [walletCopied, setWalletCopied] = useState(false);
  const walletAddress = "7gcF8Yz7DgfzxDfAEieQcRx337bKbFDeGutQNFRdcRsz";

  const handleCopyWallet = () => {
    navigator.clipboard.writeText(walletAddress);
    setWalletCopied(true);
    setTimeout(() => setWalletCopied(false), 2000);
  };

  return (
    <main className="min-h-screen bg-background">
      {/* Nav */}
      <nav className="fixed top-0 w-full h-[70px] nav-glass border-b border-border-subtle z-50 flex items-center">
        <div className="container mx-auto px-8 flex justify-between items-center">
          <Link href="/" className="font-display text-2xl font-bold text-text-primary">
            AJ<span className="text-accent">.</span>
          </Link>
          <Link href="/" className="text-text-secondary hover:text-text-primary text-sm font-medium transition-colors">
            &larr; back to portfolio
          </Link>
        </div>
      </nav>

      <div className="pt-[100px] pb-32">
        <div className="container mx-auto px-8 max-w-2xl">
          {/* Hero */}
          <div className="text-center mb-16">
            <div className="inline-flex items-center justify-center w-20 h-20 rounded-2xl bg-accent/10 border border-accent/20 mb-6">
              <i className="fa-solid fa-heart text-accent text-3xl"></i>
            </div>
            <h1 className="text-4xl md:text-5xl font-display font-semibold tracking-tight mb-4 text-text-primary">
              support open source
            </h1>
            <p className="text-lg text-text-secondary max-w-[50ch] mx-auto">
              If any of my work has helped you, consider supporting the research. Every contribution keeps the models open and the tools free.
            </p>
          </div>

          {/* Why Support */}
          <div className="bg-card border border-border-subtle rounded-2xl p-8 mb-8">
            <h2 className="text-xl font-display font-semibold mb-6 text-text-primary">what your support funds</h2>
            <ul className="space-y-4">
              <li className="flex items-start gap-3">
                <i className="fa-solid fa-microchip text-accent mt-1"></i>
                <span className="text-text-secondary">GPU compute for training and ablation experiments</span>
              </li>
              <li className="flex items-start gap-3">
                <i className="fa-solid fa-database text-accent mt-1"></i>
                <span className="text-text-secondary">Dataset curation and synthetic data generation</span>
              </li>
              <li className="flex items-start gap-3">
                <i className="fa-solid fa-code text-accent mt-1"></i>
                <span className="text-text-secondary">Maintaining open-source frameworks like DR-OPIC and Model Unfetter</span>
              </li>
              <li className="flex items-start gap-3">
                <i className="fa-solid fa-flask text-accent mt-1"></i>
                <span className="text-text-secondary">Publishing open weights and evaluation benchmarks</span>
              </li>
            </ul>
          </div>

          {/* GitHub Sponsors */}
          <div className="bg-card border border-border-subtle rounded-2xl p-8 mb-8">
            <div className="flex items-center gap-3 mb-4">
              <i className="fa-brands fa-github text-text-primary text-xl"></i>
              <h2 className="text-xl font-display font-semibold text-text-primary">github sponsors</h2>
            </div>
            <p className="text-text-secondary mb-6">
              The easiest way to support. GitHub Sponsors handles recurring and one-time donations with zero fees.
            </p>
            <a
              href="https://github.com/sponsors/josepha-mayo"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-lg font-medium bg-white text-background hover:bg-zinc-200 transition-colors"
            >
              <i className="fa-solid fa-heart"></i>
              sponsor on github
            </a>
            <p className="text-text-secondary text-xs mt-4">
              coming soon — link active once GitHub approves the sponsor profile
            </p>
          </div>

          {/* Solana / Crypto */}
          <div className="bg-card border border-border-subtle rounded-2xl p-8 mb-8">
            <div className="flex items-center gap-3 mb-4">
              <svg className="w-6 h-6 text-text-primary" viewBox="0 0 24 24" fill="currentColor">
                <path d="M4.97 16.27L12.36 2.64C12.54 2.32 13.01 2.32 13.19 2.64L20.58 16.27C20.76 16.59 20.53 17.03 20.15 17.03L17.13 17.03C16.97 17.03 16.82 16.94 16.76 16.8L14.13 11.57L12.76 14.17C12.68 14.49 12.27 14.62 12.02 14.43L8.87 12.06L4.8 16.71C4.6 16.95 4.24 16.88 4.15 16.6L4.97 16.27ZM11.39 6.99L7.34 14.71L9.79 12.83L11.39 6.99ZM16.93 14.43L14.07 14.43L12.63 11.57L15.55 11.57L16.93 14.43Z"/>
              </svg>
              <h2 className="text-xl font-display font-semibold text-text-primary">solana (SOL)</h2>
            </div>
            <p className="text-text-secondary mb-4">
              Direct wallet-to-wallet. No middleman, no fees. Send any SPL token or SOL.
            </p>
            
            <div className="bg-white/5 border border-border-subtle rounded-lg p-4">
              <p className="text-xs text-text-secondary mb-2 font-medium uppercase tracking-wider">wallet address</p>
              <div className="flex items-center gap-3">
                <code className="text-sm text-text-primary font-[family-name:var(--font-geist-mono)] break-all flex-1 select-all">
                  {walletAddress}
                </code>
                <button
                  onClick={handleCopyWallet}
                  className="text-xs px-3 py-1.5 bg-white/5 hover:bg-white/10 border border-border-subtle rounded-md text-text-secondary hover:text-text-primary transition-all whitespace-nowrap"
                >
                  {walletCopied ? (
                    <span className="flex items-center gap-1.5">
                      <i className="fa-solid fa-check text-accent"></i> copied
                    </span>
                  ) : (
                    <span className="flex items-center gap-1.5">
                      <i className="fa-regular fa-copy"></i> copy
                    </span>
                  )}
                </button>
              </div>
            </div>

            <div className="mt-6 flex items-center gap-2 text-text-secondary text-sm">
              <i className="fa-solid fa-shield-halved text-accent"></i>
              <span>verify the address matches before sending</span>
            </div>
          </div>

          {/* Thank You */}
          <div className="text-center">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-white/5 border border-border-subtle mb-4">
              <i className="fa-solid fa-sparkles text-accent text-xl"></i>
            </div>
            <p className="text-text-secondary">
              Even a star on the repo helps. Thank you for supporting open research.
            </p>
            <a
              href="https://github.com/josepha-mayo"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 mt-4 text-sm text-text-secondary hover:text-text-primary transition-colors"
            >
              <i className="fa-brands fa-github"></i>
              github.com/josepha-mayo
            </a>
          </div>
        </div>
      </div>
    </main>
  );
}
