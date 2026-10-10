import type { Metadata } from 'next';
import type { ReactNode } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import LifePhilosophy from '@/components/LifePhilosophy';
import styles from './personal.module.css';

export const metadata: Metadata = {
  title: 'outside the work | ayanda joseph',
  description: 'my favourite books and anime, japanese, guitar, chess, and my philosophy on passion, purpose, truth, and solitude.',
  alternates: { canonical: 'https://josephmayo.site/outside-the-work' },
  openGraph: {
    title: 'outside the work | ayanda joseph',
    description: 'books, music, chess, anime, and what i live for.',
    url: 'https://josephmayo.site/outside-the-work',
    type: 'website',
    images: [{ url: 'https://josephmayo.site/personal/night-dunes.webp', width: 2560, height: 1475, alt: 'sand dunes under a night sky' }],
  },
};

const books = [
  { title: 'the myth of sisyphus', author: 'albert camus', kind: 'philosophy', text: 'how do you live when the world gives you no easy explanation? i like the insistence on facing that question and living anyway.', href: 'https://www.goodreads.com/book/show/11987.The_Myth_of_Sisyphus_and_Other_Essays' },
  { title: 'crime and punishment', author: 'fyodor dostoevsky', kind: 'fiction', text: 'the way raskolnikov argues with himself. pride, guilt, and the things a person can convince himself he has the right to do.', href: 'https://www.gutenberg.org/ebooks/2554' },
  { title: 'the brothers karamazov', author: 'fyodor dostoevsky', kind: 'fiction', text: 'faith, doubt, suffering, freedom. dostoevsky gives those questions enough room to become uncomfortable. that is what draws me to him.', href: 'https://www.gutenberg.org/ebooks/28054' },
  { title: 'the computer and the brain', author: 'john von neumann', kind: 'mind & machines', text: 'von neumann thinking about computation and the brain. the relationship between those two is a question i could spend my life on.', href: 'https://yalebooks.yale.edu/book/9780300181111/the-computer-and-the-brain/' },
  { title: 'the metamorphosis', author: 'franz kafka', kind: 'fiction', text: 'what happens when a person can no longer be useful to everyone around them. the alienation in this one stayed with me.', href: 'https://www.gutenberg.org/ebooks/5200' },
  { title: 'beyond good and evil', author: 'friedrich nietzsche', kind: 'philosophy', text: 'taking a belief apart and asking where it came from. i like being made to question things i might otherwise have accepted.', href: 'https://www.gutenberg.org/ebooks/4363' },
  { title: 'man\u2019s search for meaning', author: 'viktor e. frankl', kind: 'meaning & psychology', text: 'having a reason to live through terrible circumstances. the question of purpose sits very close to my own view of life.', href: 'https://www.goodreads.com/book/show/4069.Man_s_Search_for_Meaning' },
  { title: 'can\u2019t hurt me', author: 'david goggins', kind: 'discipline', text: 'goggins is direct about discipline and the excuses we make for ourselves. that is a big part of why i like this book.', href: 'https://davidgoggins.com/book/' },
];

const practices = [
  { title: 'japanese', status: 'learning', image: '/personal/japanese.jpg', alt: 'japanese writing', icon: 'fa-language', text: 'learning to understand and speak japanese. still a long way to go.' },
  { title: 'guitar', status: 'learning', image: '/personal/guitar.jpg', alt: 'an acoustic guitar', icon: 'fa-guitar', text: 'working on chord changes and rhythm. i like having something to practise away from a screen.' },
  { title: 'chess', status: 'i play', image: '/personal/chess.jpg', alt: 'chess pieces on a board', icon: 'fa-chess-knight', text: 'i play well. i enjoy a game that gives me something difficult to calculate.' },
];

const stories = [
  { title: 'hajime no ippo', note: 'discipline', number: '02', text: 'the repetition, the training, the patience. doing the same thing until you get better at it. ippo made me appreciate that part of the work.', href: 'https://www.crunchyroll.com/series/GW4HM7N7X/hajime-no-ippo-the-fighting' },
  { title: 'dr. stone', note: 'senku / curiosity', number: '03', text: 'senku makes me want to learn. asking how something works, trying it, getting it wrong, trying again. i love seeing knowledge turn into something useful.', href: 'https://www.crunchyroll.com/series/GYEXQKJG6/dr-stone' },
  { title: 'kaiji', note: 'psychology under pressure', number: '04', text: 'the mind games and the pressure. how differently people behave when they have something to lose, and how much it matters to understand the rules you are playing by.', href: 'https://www.crunchyroll.com/series/G6GGV5WW6/kaiji' },
  { title: 'major', note: 'a life spent chasing something', number: '05', text: 'goro growing up with the same ambition. the setbacks, starting again, carrying that desire through years of his life. i love following a story for that long.', href: 'https://www.crunchyroll.com/search?q=major' },
];

function SectionHeading({ number, title, children }: { number: string; title: string; children?: ReactNode }) {
  return (
    <div className={styles.sectionHeading}>
      <span className={styles.sectionNumber}>{number}</span>
      <div><h2>{title}</h2>{children && <p>{children}</p>}</div>
    </div>
  );
}

function RecommendedLink({ href, title }: { href: string; title: string }) {
  return (
    <a href={href} target="_blank" rel="noopener noreferrer" className={styles.recommended} aria-label={`personally recommended: ${title} (opens in a new tab)`}>
      personally recommended <span aria-hidden="true">↗</span>
    </a>
  );
}

export default function OutsideTheWork() {
  return (
    <div className={styles.page}>
      <nav className="fixed top-0 w-full h-[70px] nav-glass border-b border-border-subtle z-50 flex items-center" aria-label="personal page">
        <div className="container mx-auto px-6 md:px-8 flex justify-between items-center">
          <Link href="/" className="font-display text-2xl font-bold text-text-primary" aria-label="ayanda joseph, home">aj<span className="text-accent">.</span></Link>
          <Link href="/" className={styles.backLink}><span aria-hidden="true">←</span> back to the work</Link>
        </div>
      </nav>

      <main id="main">
        <header className={styles.hero}>
          <div className={styles.heroBackdrop} aria-hidden="true">
            <Image src="/personal/night-dunes.webp" alt="" fill sizes="100vw" priority unoptimized className={styles.landscapeImage} />
          </div>
          <div className={styles.heroShade} aria-hidden="true" />
          <div className={`${styles.container} ${styles.heroContent}`}>
            <p className={styles.eyebrow}><span className={styles.smallSquare} aria-hidden="true" />ayanda joseph</p>
            <h1>outside<br />the work<span className={styles.accent}>.</span></h1>
            <p className={styles.heroIntro}>books, music, chess, anime, and what i live for.</p>
            <nav aria-label="on this page" className={styles.chapterNav}>
              <a href="#books"><span>01</span> books</a>
              <a href="#practice"><span>02</span> practice</a>
              <a href="#philosophy"><span>03</span> philosophy</a>
              <a href="#stories"><span>04</span> anime</a>
            </nav>
          </div>
        </header>

        <section id="books" className={`${styles.container} ${styles.section}`} aria-label="my favourite books">
          <SectionHeading number="01" title="my favourite books">a few from the shelf. i recommend them.</SectionHeading>
          <div className={styles.bookGrid}>
            {books.map((book, index) => (
              <article key={book.title} className={styles.book}>
                <div className={styles.bookTop}><span className={styles.bookNumber}>{String(index + 1).padStart(2, '0')}</span><span className={styles.bookKind}>{book.kind}</span></div>
                <div className={styles.bookText}><h3>{book.title}</h3><p className={styles.bookAuthor}>{book.author}</p><p className={styles.bookDescription}>{book.text}</p></div>
                <RecommendedLink href={book.href} title={book.title} />
              </article>
            ))}
          </div>
        </section>

        <section id="practice" className={`${styles.container} ${styles.section}`} aria-label="learning and hobbies">
          <SectionHeading number="02" title="away from the keyboard" />
          <div className={styles.practiceGrid}>
            {practices.map((practice) => (
              <article key={practice.title} className={styles.practiceCard}>
                <div className={styles.practiceImage}><Image src={practice.image} alt={practice.alt} fill sizes="(min-width: 900px) 33vw, (min-width: 640px) 50vw, 100vw" /><span className={styles.practiceStatus}>{practice.status}</span></div>
                <div className={styles.practiceCopy}><h3><i className={`fa-solid ${practice.icon}`} aria-hidden="true" />{practice.title}</h3><p>{practice.text}</p></div>
              </article>
            ))}
          </div>
        </section>

        <section id="philosophy" className={`${styles.container} ${styles.section}`} aria-label="my philosophy on life">
          <div className={styles.philosophyPanel}><span className={styles.philosophyNumber} aria-hidden="true">03 / life</span><LifePhilosophy /></div>
        </section>

        <section id="stories" className={`${styles.container} ${styles.section}`} aria-label="anime i recommend">
          <SectionHeading number="04" title="anime i recommend">i recommend these. they changed me positively.</SectionHeading>
          <article className={styles.joeFeature}>
            <div className={styles.joeImage}><Image src="/personal/joe-sharp.webp" alt="joe yabuki in his cap and coat beneath an orange sky" fill sizes="(min-width: 900px) 460px, (min-width: 640px) 40vw, 100vw" unoptimized /></div>
            <div className={styles.joeCopy}>
              <p className={styles.eyebrow}>01 / my favourite</p>
              <h3>ashita no joe</h3>
              <p>joe is obsession. taking one thing and giving it everything. the relentless work, the solitude, the sorrow. boxing becomes his whole life.</p>
              <p>the story shows the cost of that obsession in his body and his relationships. what stayed with me is his absolute sense of purpose. he keeps reaching for the same thing through every loss. it changed what having something to live for means to me.</p>
              <RecommendedLink href="https://www.crunchyroll.com/series/GYNQP722Y/tomorrows-joe" title="ashita no joe" />
            </div>
          </article>
          <div className={styles.storyGrid}>
            {stories.map((story) => (
              <article key={story.title} className={styles.storyCard}>
                <div className={styles.storyTop}><span>{story.number}</span><span>{story.note}</span></div>
                <h3>{story.title}</h3><p className={styles.storyDescription}>{story.text}</p>
                <RecommendedLink href={story.href} title={story.title} />
              </article>
            ))}
          </div>
        </section>
      </main>

      <footer className={styles.footer}>
        <div className={styles.container}>
          <div className={styles.footerLinks}><Link href="/" className={styles.primaryLink}>back to the work <span aria-hidden="true">→</span></Link></div>
          <div className={styles.footerBottom}><p>© {new Date().getFullYear()} ayanda joseph.</p><span>outside the work.</span></div>
        </div>
      </footer>
    </div>
  );
}
