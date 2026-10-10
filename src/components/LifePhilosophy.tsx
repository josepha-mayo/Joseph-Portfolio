type LifePhilosophyProps = {
  compact?: boolean;
};

export default function LifePhilosophy({ compact = false }: LifePhilosophyProps) {
  return (
    <div className={compact ? 'max-w-4xl mx-auto' : ''}>
      <p className="text-mono text-xs tracking-[0.16em] text-accent mb-5">my philosophy</p>
      <h2 className="font-display text-3xl md:text-4xl font-semibold tracking-tight mb-8">something to live for</h2>

      <figure className="mb-9 border-l-2 border-accent/70 pl-6 md:pl-8">
        <blockquote className="font-display text-xl md:text-2xl leading-relaxed text-text-primary max-w-3xl">
          <p>&ldquo;for the secret of man&apos;s being is not only to live but to have something to live for.&rdquo;</p>
        </blockquote>
        <figcaption className="mt-4 text-xs text-text-secondary">
          <a href="https://www.gutenberg.org/cache/epub/28054/pg28054-images.html" target="_blank" rel="noopener noreferrer" className="hover:text-accent transition-colors">fyodor dostoevsky, the brothers karamazov</a>
        </figcaption>
      </figure>

      <div className="space-y-5 text-text-secondary text-base md:text-lg leading-relaxed max-w-3xl">
        <p className="text-text-primary">i go by the religion of passion.</p>
        <p>
          i believe life is given to us not just to live, but to add value to the earth.
          to chase something greater than ourselves, till the end of our lives.
          to find something worth being obsessed with, and be willing to go far for it.
          i want to give my life to something that matters.
        </p>
        <p>
          i&apos;m searching for truth in its purest form, in whatever way it occurs to me.
          i want to follow it wherever it leads, even when it asks me to change what i believe.
        </p>
        <p>
          solitude gives me room to think extensively. to sit with a question for hours,
          follow it further, and work out what i actually think. i value that space.
        </p>
      </div>

      <figure className="mt-10 border-t border-border-subtle pt-8">
        <blockquote className="font-display text-xl md:text-2xl leading-relaxed text-text-primary max-w-3xl">
          <p>&ldquo;let it offend you that someone else can be handed your days and turn them into something greater&rdquo;</p>
        </blockquote>
        <figcaption className="mt-4 text-xs text-text-secondary">seneca</figcaption>
      </figure>
    </div>
  );
}
