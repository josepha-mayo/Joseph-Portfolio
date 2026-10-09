type LifePhilosophyProps = {
  compact?: boolean;
};

export default function LifePhilosophy({ compact = false }: LifePhilosophyProps) {
  return (
    <div className={compact ? 'max-w-4xl mx-auto' : ''}>
      <p className="text-mono text-xs tracking-[0.16em] text-accent mb-5">a reminder to myself</p>
      <h2 className="font-display text-3xl md:text-4xl font-semibold tracking-tight mb-6">how i try to live</h2>
      <p className="text-text-secondary text-base md:text-lg leading-relaxed max-w-3xl">
        i don&apos;t think meaning is handed to you. i think you build it, through what you learn,
        what you make, and what you keep showing up for. i care about getting better for real,
        not just looking like i am. i want to do something worthwhile with the life i have.
      </p>
      <figure className="mt-9 border-l-2 border-accent/70 pl-6 md:pl-8">
        <blockquote className="font-display text-xl md:text-2xl leading-relaxed text-text-primary max-w-3xl">
          <p>&ldquo;let it offend you that someone else can be handed your days and turn them into something greater&rdquo;</p>
        </blockquote>
        <figcaption className="mt-5 text-xs leading-relaxed text-text-secondary">
          attributed to seneca <span aria-hidden="true">·</span> original source unverified
        </figcaption>
      </figure>
    </div>
  );
}
